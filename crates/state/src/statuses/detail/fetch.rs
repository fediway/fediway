use std::collections::{HashMap, HashSet};

use common::ids::{AccountId, StatusId};
use common::paperclip::MediaConfig;
use mastodon::{Quote, Status};
use sqlx::{Executor, PgPool, Postgres};

use super::row::{
    BaseRow, CardRow, EmojiRow, Enrichment, MediaRow, MentionRow, StatsRow, StatsTuple,
    ViewerState, build_status, scan_shortcodes,
};
use super::sql::{BASE_QUERY, CARD_QUERY, MEDIA_QUERY};

#[tracing::instrument(
    skip(db, media),
    name = "db.statuses.detail.fetch_by_ids",
    fields(ids_len = ids.len(), viewer = ?viewer),
)]
pub async fn fetch_by_ids(
    db: &PgPool,
    instance_domain: &str,
    media: &MediaConfig,
    ids: &[StatusId],
    viewer: Option<AccountId>,
) -> Result<Vec<Status>, crate::Error> {
    let mut statuses = fetch_enriched(db, instance_domain, media, ids, viewer).await?;
    if statuses.is_empty() {
        return Ok(statuses);
    }

    let resolved_ids: Vec<StatusId> = statuses
        .iter()
        .filter_map(|s| s.id.parse::<i64>().ok().map(StatusId))
        .collect();
    let quote_targets = fetch_quote_targets(db, &resolved_ids).await?;
    if quote_targets.is_empty() {
        return Ok(statuses);
    }

    let target_ids: Vec<StatusId> = quote_targets.values().copied().collect();
    let parents = fetch_enriched(db, instance_domain, media, &target_ids, viewer).await?;
    let parent_by_id: HashMap<StatusId, Status> = parents
        .into_iter()
        .filter_map(|s| s.id.parse::<i64>().ok().map(|id| (StatusId(id), s)))
        .collect();

    for status in &mut statuses {
        let Ok(sid) = status.id.parse::<i64>().map(StatusId) else {
            continue;
        };
        let Some(quoted_id) = quote_targets.get(&sid) else {
            continue;
        };
        if let Some(parent) = parent_by_id.get(quoted_id).cloned() {
            status.quote = Some(Quote {
                state: "accepted",
                quoted_status: Box::new(parent),
            });
        }
    }

    Ok(statuses)
}

#[tracing::instrument(
    skip(db, media),
    name = "db.statuses.detail.fetch_enriched",
    fields(ids_len = ids.len(), viewer = ?viewer),
)]
async fn fetch_enriched(
    db: &PgPool,
    instance_domain: &str,
    media: &MediaConfig,
    ids: &[StatusId],
    viewer: Option<AccountId>,
) -> Result<Vec<Status>, crate::Error> {
    if ids.is_empty() {
        return Ok(Vec::new());
    }

    let base = fetch_base(db, ids).await?;
    if base.is_empty() {
        return Ok(Vec::new());
    }

    let resolved_ids: Vec<StatusId> = base.iter().map(|r| r.id).collect();

    let (stats, media_map, tags, cards, mentions_map, viewer) = tokio::try_join!(
        fetch_stats(db, &resolved_ids),
        fetch_media(db, &resolved_ids),
        fetch_tags(db, &resolved_ids),
        fetch_cards(db, &resolved_ids),
        fetch_mentions(db, &resolved_ids),
        fetch_viewer_state(db, viewer, &resolved_ids),
    )?;

    let shortcodes = scan_shortcodes(&base);
    let emojis = if shortcodes.is_empty() {
        HashMap::new()
    } else {
        fetch_emojis(db, &shortcodes).await?
    };

    let enrichment = Enrichment {
        stats: &stats,
        media: &media_map,
        tags: &tags,
        cards: &cards,
        mentions: &mentions_map,
        emojis: &emojis,
        viewer: &viewer,
    };

    Ok(base
        .into_iter()
        .map(|row| build_status(row, instance_domain, media, &enrichment))
        .collect())
}

#[tracing::instrument(
    skip(db),
    name = "db.statuses.detail.fetch_viewer_state",
    fields(ids_len = ids.len(), viewer = ?viewer),
)]
async fn fetch_viewer_state(
    db: &PgPool,
    viewer: Option<AccountId>,
    ids: &[StatusId],
) -> Result<ViewerState, crate::Error> {
    let Some(viewer) = viewer else {
        return Ok(ViewerState::default());
    };
    if ids.is_empty() {
        return Ok(ViewerState::default());
    }

    let (favourited, bookmarked, reblogged) = tokio::try_join!(
        fetch_viewer_id_set(
            db,
            "SELECT status_id FROM favourites
             WHERE account_id = $1 AND status_id = ANY($2::bigint[])",
            viewer,
            ids,
        ),
        fetch_viewer_id_set(
            db,
            "SELECT status_id FROM bookmarks
             WHERE account_id = $1 AND status_id = ANY($2::bigint[])",
            viewer,
            ids,
        ),
        fetch_viewer_id_set(
            db,
            "SELECT reblog_of_id FROM statuses
             WHERE account_id = $1
               AND reblog_of_id = ANY($2::bigint[])
               AND deleted_at IS NULL",
            viewer,
            ids,
        ),
    )?;

    Ok(ViewerState {
        favourited,
        bookmarked,
        reblogged,
    })
}

#[tracing::instrument(
    skip(e, query),
    name = "db.statuses.detail.fetch_viewer_id_set",
    fields(ids_len = ids.len(), viewer = ?viewer),
)]
async fn fetch_viewer_id_set(
    e: impl Executor<'_, Database = Postgres>,
    query: &str,
    viewer: AccountId,
    ids: &[StatusId],
) -> Result<HashSet<StatusId>, crate::Error> {
    let raw: Vec<i64> = ids.iter().map(|s| s.0).collect();
    let rows = sqlx::query_scalar::<_, i64>(query)
        .bind(viewer)
        .bind(&raw)
        .fetch_all(e)
        .await?;
    Ok(rows.into_iter().map(StatusId).collect())
}

#[tracing::instrument(
    skip(e),
    name = "db.statuses.detail.fetch_base",
    fields(ids_len = ids.len()),
)]
async fn fetch_base(
    e: impl Executor<'_, Database = Postgres>,
    ids: &[StatusId],
) -> Result<Vec<BaseRow>, crate::Error> {
    let raw: Vec<i64> = ids.iter().map(|s| s.0).collect();
    Ok(sqlx::query_as::<_, BaseRow>(BASE_QUERY)
        .bind(&raw)
        .fetch_all(e)
        .await?)
}

#[tracing::instrument(
    skip(e),
    name = "db.statuses.detail.fetch_stats",
    fields(ids_len = ids.len()),
)]
async fn fetch_stats(
    e: impl Executor<'_, Database = Postgres>,
    ids: &[StatusId],
) -> Result<HashMap<StatusId, StatsRow>, crate::Error> {
    let raw: Vec<i64> = ids.iter().map(|s| s.0).collect();
    let query = "SELECT status_id, replies_count, reblogs_count, favourites_count, quotes_count
                 FROM status_stats WHERE status_id = ANY($1::bigint[])";
    let rows = sqlx::query_as::<_, StatsTuple>(query)
        .bind(&raw)
        .fetch_all(e)
        .await?;
    Ok(rows
        .into_iter()
        .map(|r| {
            (
                r.status_id,
                StatsRow {
                    replies: r.replies_count,
                    reblogs: r.reblogs_count,
                    favourites: r.favourites_count,
                    quotes: r.quotes_count,
                },
            )
        })
        .collect())
}

#[tracing::instrument(
    skip(e),
    name = "db.statuses.detail.fetch_media",
    fields(ids_len = ids.len()),
)]
async fn fetch_media(
    e: impl Executor<'_, Database = Postgres>,
    ids: &[StatusId],
) -> Result<HashMap<StatusId, Vec<MediaRow>>, crate::Error> {
    let raw: Vec<i64> = ids.iter().map(|s| s.0).collect();
    let rows = sqlx::query_as::<_, MediaRow>(MEDIA_QUERY)
        .bind(&raw)
        .fetch_all(e)
        .await?;
    let mut map: HashMap<StatusId, Vec<MediaRow>> = HashMap::new();
    for row in rows {
        map.entry(row.status_id).or_default().push(row);
    }
    Ok(map)
}

#[tracing::instrument(
    skip(e),
    name = "db.statuses.detail.fetch_tags",
    fields(ids_len = ids.len()),
)]
async fn fetch_tags(
    e: impl Executor<'_, Database = Postgres>,
    ids: &[StatusId],
) -> Result<HashMap<StatusId, Vec<String>>, crate::Error> {
    let raw: Vec<i64> = ids.iter().map(|s| s.0).collect();
    let rows: Vec<(StatusId, String)> = sqlx::query_as(
        "SELECT st.status_id, t.name
         FROM statuses_tags st
         JOIN tags t ON t.id = st.tag_id
         WHERE st.status_id = ANY($1::bigint[])
         ORDER BY st.status_id, t.name",
    )
    .bind(&raw)
    .fetch_all(e)
    .await?;
    let mut map: HashMap<StatusId, Vec<String>> = HashMap::new();
    for (sid, name) in rows {
        map.entry(sid).or_default().push(name);
    }
    Ok(map)
}

#[tracing::instrument(
    skip(e),
    name = "db.statuses.detail.fetch_cards",
    fields(ids_len = ids.len()),
)]
async fn fetch_cards(
    e: impl Executor<'_, Database = Postgres>,
    ids: &[StatusId],
) -> Result<HashMap<StatusId, CardRow>, crate::Error> {
    let raw: Vec<i64> = ids.iter().map(|s| s.0).collect();
    let rows = sqlx::query_as::<_, CardRow>(CARD_QUERY)
        .bind(&raw)
        .fetch_all(e)
        .await?;
    Ok(rows.into_iter().map(|r| (r.status_id, r)).collect())
}

#[tracing::instrument(
    skip(e),
    name = "db.statuses.detail.fetch_mentions",
    fields(ids_len = ids.len()),
)]
async fn fetch_mentions(
    e: impl Executor<'_, Database = Postgres>,
    ids: &[StatusId],
) -> Result<HashMap<StatusId, Vec<MentionRow>>, crate::Error> {
    let raw: Vec<i64> = ids.iter().map(|s| s.0).collect();
    let query = r"
        SELECT m.status_id, a.id AS account_id, a.username, a.domain, a.url
        FROM mentions m
        JOIN accounts a ON a.id = m.account_id
        WHERE m.status_id = ANY($1::bigint[])
        ORDER BY m.status_id, m.id
    ";
    let rows = sqlx::query_as::<_, MentionRow>(query)
        .bind(&raw)
        .fetch_all(e)
        .await?;
    let mut map: HashMap<StatusId, Vec<MentionRow>> = HashMap::new();
    for row in rows {
        map.entry(row.status_id).or_default().push(row);
    }
    Ok(map)
}

#[tracing::instrument(
    skip(e),
    name = "db.statuses.detail.fetch_emojis",
    fields(shortcodes_len = shortcodes.len()),
)]
async fn fetch_emojis(
    e: impl Executor<'_, Database = Postgres>,
    shortcodes: &HashSet<String>,
) -> Result<HashMap<String, EmojiRow>, crate::Error> {
    let codes: Vec<&str> = shortcodes.iter().map(String::as_str).collect();
    let query = r"
        SELECT id, shortcode, domain, image_file_name, image_remote_url, image_storage_schema_version
        FROM custom_emojis
        WHERE disabled = FALSE AND shortcode = ANY($1::text[])
        ORDER BY domain IS NOT NULL, shortcode
    ";
    let rows = sqlx::query_as::<_, EmojiRow>(query)
        .bind(&codes)
        .fetch_all(e)
        .await?;
    let mut map: HashMap<String, EmojiRow> = HashMap::new();
    for row in rows {
        map.entry(row.shortcode.clone()).or_insert(row);
    }
    Ok(map)
}

#[tracing::instrument(
    skip(e),
    name = "db.statuses.detail.fetch_quote_targets",
    fields(ids_len = ids.len()),
)]
async fn fetch_quote_targets(
    e: impl Executor<'_, Database = Postgres>,
    ids: &[StatusId],
) -> Result<HashMap<StatusId, StatusId>, crate::Error> {
    let raw: Vec<i64> = ids.iter().map(|s| s.0).collect();
    let query = r"
        SELECT status_id, quoted_status_id
        FROM quotes
        WHERE status_id = ANY($1::bigint[])
          AND state = 1
          AND quoted_status_id IS NOT NULL
    ";
    let rows: Vec<(StatusId, StatusId)> = sqlx::query_as(query).bind(&raw).fetch_all(e).await?;
    Ok(rows.into_iter().collect())
}
