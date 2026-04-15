use std::collections::{HashMap, HashSet};

use chrono::{DateTime, NaiveDateTime, Utc};
use common::paperclip::MediaConfig;
use mastodon::sanitize::{sanitize_html, sanitize_text};
use mastodon::{
    Account, CustomEmoji, Field, MediaAttachment, MediaMeta, MediaMetaDimensions, Mention,
    PreviewCard, PreviewCardAuthor, Quote, QuoteApproval, Status, Tag,
};
use regex::Regex;
use serde::Deserialize;
use sqlx::{FromRow, PgPool};

pub async fn fetch_by_ids(
    db: &PgPool,
    instance_domain: &str,
    media: &MediaConfig,
    ids: &[i64],
    viewer_account_id: Option<i64>,
) -> Vec<Status> {
    let mut statuses = fetch_enriched(db, instance_domain, media, ids, viewer_account_id).await;
    if statuses.is_empty() {
        return statuses;
    }

    let resolved_ids: Vec<i64> = statuses
        .iter()
        .filter_map(|s| s.id.parse::<i64>().ok())
        .collect();
    let quote_targets = fetch_quote_targets(db, &resolved_ids).await;
    if quote_targets.is_empty() {
        return statuses;
    }

    let target_ids: Vec<i64> = quote_targets.values().copied().collect();
    let parents = fetch_enriched(db, instance_domain, media, &target_ids, viewer_account_id).await;
    let parent_by_id: HashMap<i64, Status> = parents
        .into_iter()
        .filter_map(|s| s.id.parse::<i64>().ok().map(|id| (id, s)))
        .collect();

    for status in &mut statuses {
        let Ok(sid) = status.id.parse::<i64>() else {
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

    statuses
}

async fn fetch_enriched(
    db: &PgPool,
    instance_domain: &str,
    media: &MediaConfig,
    ids: &[i64],
    viewer_account_id: Option<i64>,
) -> Vec<Status> {
    if ids.is_empty() {
        return Vec::new();
    }

    let base = fetch_base(db, ids).await;
    if base.is_empty() {
        return Vec::new();
    }

    let resolved_ids: Vec<i64> = base.iter().map(|r| r.id).collect();

    let (stats, media_map, tags, cards, mentions_map, viewer) = tokio::join!(
        fetch_stats(db, &resolved_ids),
        fetch_media(db, &resolved_ids),
        fetch_tags(db, &resolved_ids),
        fetch_cards(db, &resolved_ids),
        fetch_mentions(db, &resolved_ids),
        fetch_viewer_state(db, viewer_account_id, &resolved_ids),
    );

    let shortcodes = scan_shortcodes(&base);
    let emojis = if shortcodes.is_empty() {
        HashMap::new()
    } else {
        fetch_emojis(db, &shortcodes).await
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

    base.into_iter()
        .map(|row| build_status(row, instance_domain, media, &enrichment))
        .collect()
}

struct Enrichment<'a> {
    stats: &'a HashMap<i64, StatsRow>,
    media: &'a HashMap<i64, Vec<MediaRow>>,
    tags: &'a HashMap<i64, Vec<String>>,
    cards: &'a HashMap<i64, CardRow>,
    mentions: &'a HashMap<i64, Vec<MentionRow>>,
    emojis: &'a HashMap<String, EmojiRow>,
    viewer: &'a ViewerState,
}

#[derive(Default)]
struct ViewerState {
    favourited: HashSet<i64>,
    bookmarked: HashSet<i64>,
    reblogged: HashSet<i64>,
}

async fn fetch_viewer_state(db: &PgPool, viewer: Option<i64>, ids: &[i64]) -> ViewerState {
    let Some(viewer) = viewer else {
        return ViewerState::default();
    };
    if ids.is_empty() {
        return ViewerState::default();
    }

    let (favourited, bookmarked, reblogged) = tokio::join!(
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
    );

    ViewerState {
        favourited,
        bookmarked,
        reblogged,
    }
}

async fn fetch_viewer_id_set(db: &PgPool, query: &str, viewer: i64, ids: &[i64]) -> HashSet<i64> {
    match sqlx::query_scalar::<_, i64>(query)
        .bind(viewer)
        .bind(ids)
        .fetch_all(db)
        .await
    {
        Ok(rows) => rows.into_iter().collect(),
        Err(e) => {
            tracing::warn!(error = %e, "status view: viewer state query failed");
            HashSet::new()
        }
    }
}

#[derive(FromRow)]
struct BaseRow {
    id: i64,
    account_id: i64,
    uri: Option<String>,
    url: Option<String>,
    text: String,
    spoiler_text: String,
    sensitive: bool,
    language: Option<String>,
    in_reply_to_id: Option<i64>,
    in_reply_to_account_id: Option<i64>,
    created_at: NaiveDateTime,
    edited_at: Option<NaiveDateTime>,
    username: String,
    domain: Option<String>,
    display_name: String,
    note: String,
    account_url: Option<String>,
    account_uri: String,
    avatar_file_name: Option<String>,
    avatar_remote_url: Option<String>,
    header_file_name: Option<String>,
    header_remote_url: String,
    account_created_at: NaiveDateTime,
    discoverable: Option<bool>,
    indexable: bool,
    locked: bool,
    actor_type: Option<String>,
    fields: Option<serde_json::Value>,
    statuses_count: i64,
    following_count: i64,
    followers_count: i64,
    last_status_at: Option<NaiveDateTime>,
}

const BASE_QUERY: &str = r"
    SELECT
        s.id,
        s.account_id,
        s.uri,
        s.url,
        s.text,
        s.spoiler_text,
        s.sensitive,
        s.language,
        s.in_reply_to_id,
        s.in_reply_to_account_id,
        s.created_at,
        s.edited_at,
        a.username,
        a.domain,
        a.display_name,
        a.note,
        a.url AS account_url,
        a.uri AS account_uri,
        a.avatar_file_name,
        a.avatar_remote_url,
        a.header_file_name,
        a.header_remote_url,
        a.created_at AS account_created_at,
        a.discoverable,
        a.indexable,
        a.locked,
        a.actor_type,
        a.fields,
        COALESCE(ast.statuses_count, 0)::bigint  AS statuses_count,
        COALESCE(ast.following_count, 0)::bigint AS following_count,
        COALESCE(ast.followers_count, 0)::bigint AS followers_count,
        ast.last_status_at
    FROM statuses s
    JOIN accounts a ON a.id = s.account_id
    LEFT JOIN account_stats ast ON ast.account_id = a.id
    WHERE s.id = ANY($1::bigint[])
      AND s.deleted_at IS NULL
      AND a.suspended_at IS NULL
      AND a.silenced_at IS NULL
      AND s.visibility IN (0, 1)
      AND s.reblog_of_id IS NULL
    ORDER BY array_position($1::bigint[], s.id)
";

async fn fetch_base(db: &PgPool, ids: &[i64]) -> Vec<BaseRow> {
    match sqlx::query_as::<_, BaseRow>(BASE_QUERY)
        .bind(ids)
        .fetch_all(db)
        .await
    {
        Ok(rows) => rows,
        Err(e) => {
            tracing::warn!(error = %e, "status view: base query failed");
            Vec::new()
        }
    }
}

#[derive(Default, Clone)]
struct StatsRow {
    replies: i64,
    reblogs: i64,
    favourites: i64,
    quotes: i64,
}

#[derive(FromRow)]
struct StatsTuple {
    status_id: i64,
    replies_count: i64,
    reblogs_count: i64,
    favourites_count: i64,
    quotes_count: i64,
}

async fn fetch_stats(db: &PgPool, ids: &[i64]) -> HashMap<i64, StatsRow> {
    let query = "SELECT status_id, replies_count, reblogs_count, favourites_count, quotes_count
                 FROM status_stats WHERE status_id = ANY($1::bigint[])";
    match sqlx::query_as::<_, StatsTuple>(query)
        .bind(ids)
        .fetch_all(db)
        .await
    {
        Ok(rows) => rows
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
            .collect(),
        Err(e) => {
            tracing::warn!(error = %e, "status view: stats query failed");
            HashMap::new()
        }
    }
}

#[derive(FromRow)]
struct MediaRow {
    id: i64,
    status_id: i64,
    media_type: i32,
    description: Option<String>,
    remote_url: String,
    blurhash: Option<String>,
    file_file_name: Option<String>,
    file_meta: Option<serde_json::Value>,
    thumbnail_file_name: Option<String>,
    account_is_local: bool,
}

const MEDIA_QUERY: &str = r"
    SELECT
        ma.id,
        ma.status_id,
        ma.type AS media_type,
        ma.description,
        ma.remote_url,
        ma.blurhash,
        ma.file_file_name,
        ma.file_meta,
        ma.thumbnail_file_name,
        (a.domain IS NULL) AS account_is_local
    FROM media_attachments ma
    JOIN statuses s ON s.id = ma.status_id
    JOIN accounts a ON a.id = s.account_id
    WHERE ma.status_id = ANY($1::bigint[])
    ORDER BY
        ma.status_id,
        array_position(s.ordered_media_attachment_ids, ma.id) NULLS LAST,
        ma.id
";

async fn fetch_media(db: &PgPool, ids: &[i64]) -> HashMap<i64, Vec<MediaRow>> {
    match sqlx::query_as::<_, MediaRow>(MEDIA_QUERY)
        .bind(ids)
        .fetch_all(db)
        .await
    {
        Ok(rows) => {
            let mut map: HashMap<i64, Vec<MediaRow>> = HashMap::new();
            for row in rows {
                map.entry(row.status_id).or_default().push(row);
            }
            map
        }
        Err(e) => {
            tracing::warn!(error = %e, "status view: media query failed");
            HashMap::new()
        }
    }
}

async fn fetch_tags(db: &PgPool, ids: &[i64]) -> HashMap<i64, Vec<String>> {
    let rows: Result<Vec<(i64, String)>, _> = sqlx::query_as(
        "SELECT st.status_id, t.name
         FROM statuses_tags st
         JOIN tags t ON t.id = st.tag_id
         WHERE st.status_id = ANY($1::bigint[])
         ORDER BY st.status_id, t.name",
    )
    .bind(ids)
    .fetch_all(db)
    .await;
    match rows {
        Ok(rows) => {
            let mut map: HashMap<i64, Vec<String>> = HashMap::new();
            for (sid, name) in rows {
                map.entry(sid).or_default().push(name);
            }
            map
        }
        Err(e) => {
            tracing::warn!(error = %e, "status view: tags query failed");
            HashMap::new()
        }
    }
}

#[derive(FromRow)]
struct CardRow {
    status_id: i64,
    id: i64,
    url: String,
    title: String,
    description: String,
    card_type: i32,
    html: String,
    author_name: String,
    author_url: String,
    provider_name: String,
    provider_url: String,
    image_file_name: Option<String>,
    image_description: String,
    width: i32,
    height: i32,
    embed_url: String,
    blurhash: Option<String>,
}

const CARD_QUERY: &str = r"
    SELECT DISTINCT ON (pcs.status_id)
        pcs.status_id,
        pc.id,
        pc.url,
        pc.title,
        pc.description,
        pc.type AS card_type,
        pc.html,
        pc.author_name,
        pc.author_url,
        pc.provider_name,
        pc.provider_url,
        pc.image_file_name,
        pc.image_description,
        pc.width,
        pc.height,
        pc.embed_url,
        pc.blurhash
    FROM preview_cards_statuses pcs
    JOIN preview_cards pc ON pc.id = pcs.preview_card_id
    WHERE pcs.status_id = ANY($1::bigint[])
    ORDER BY pcs.status_id, pc.id
";

async fn fetch_cards(db: &PgPool, ids: &[i64]) -> HashMap<i64, CardRow> {
    match sqlx::query_as::<_, CardRow>(CARD_QUERY)
        .bind(ids)
        .fetch_all(db)
        .await
    {
        Ok(rows) => rows.into_iter().map(|r| (r.status_id, r)).collect(),
        Err(e) => {
            tracing::warn!(error = %e, "status view: cards query failed");
            HashMap::new()
        }
    }
}

#[derive(FromRow)]
struct MentionRow {
    status_id: i64,
    account_id: i64,
    username: String,
    domain: Option<String>,
    url: Option<String>,
}

async fn fetch_mentions(db: &PgPool, ids: &[i64]) -> HashMap<i64, Vec<MentionRow>> {
    let query = r"
        SELECT m.status_id, a.id AS account_id, a.username, a.domain, a.url
        FROM mentions m
        JOIN accounts a ON a.id = m.account_id
        WHERE m.status_id = ANY($1::bigint[])
        ORDER BY m.status_id, m.id
    ";
    match sqlx::query_as::<_, MentionRow>(query)
        .bind(ids)
        .fetch_all(db)
        .await
    {
        Ok(rows) => {
            let mut map: HashMap<i64, Vec<MentionRow>> = HashMap::new();
            for row in rows {
                map.entry(row.status_id).or_default().push(row);
            }
            map
        }
        Err(e) => {
            tracing::warn!(error = %e, "status view: mentions query failed");
            HashMap::new()
        }
    }
}

#[derive(FromRow)]
struct EmojiRow {
    id: i64,
    shortcode: String,
    domain: Option<String>,
    image_file_name: Option<String>,
    image_remote_url: Option<String>,
}

async fn fetch_emojis(db: &PgPool, shortcodes: &HashSet<String>) -> HashMap<String, EmojiRow> {
    let codes: Vec<&str> = shortcodes.iter().map(String::as_str).collect();
    let query = r"
        SELECT id, shortcode, domain, image_file_name, image_remote_url
        FROM custom_emojis
        WHERE disabled = FALSE AND shortcode = ANY($1::text[])
        ORDER BY domain IS NOT NULL, shortcode
    ";
    match sqlx::query_as::<_, EmojiRow>(query)
        .bind(&codes)
        .fetch_all(db)
        .await
    {
        Ok(rows) => {
            let mut map: HashMap<String, EmojiRow> = HashMap::new();
            for row in rows {
                map.entry(row.shortcode.clone()).or_insert(row);
            }
            map
        }
        Err(e) => {
            tracing::warn!(error = %e, "status view: emojis query failed");
            HashMap::new()
        }
    }
}

async fn fetch_quote_targets(db: &PgPool, ids: &[i64]) -> HashMap<i64, i64> {
    let query = r"
        SELECT status_id, quoted_status_id
        FROM quotes
        WHERE status_id = ANY($1::bigint[])
          AND state = 1
          AND quoted_status_id IS NOT NULL
    ";
    let rows: Result<Vec<(i64, i64)>, _> = sqlx::query_as(query).bind(ids).fetch_all(db).await;
    match rows {
        Ok(rows) => rows.into_iter().collect(),
        Err(e) => {
            tracing::warn!(error = %e, "status view: quotes query failed");
            HashMap::new()
        }
    }
}

fn build_status(
    row: BaseRow,
    instance_domain: &str,
    media: &MediaConfig,
    enrich: &Enrichment<'_>,
) -> Status {
    let status_id = row.id;
    let stat = enrich.stats.get(&status_id).cloned().unwrap_or_default();

    let account = build_account(&row, instance_domain, media, enrich.emojis);

    let media_attachments = enrich
        .media
        .get(&status_id)
        .map(|rows| {
            rows.iter()
                .map(|m| build_media_attachment(m, media))
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let tag_list = enrich
        .tags
        .get(&status_id)
        .map(|names| {
            names
                .iter()
                .map(|name| Tag {
                    name: name.clone(),
                    url: format!("https://{instance_domain}/tags/{name}"),
                    history: Vec::new(),
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let mention_list = enrich
        .mentions
        .get(&status_id)
        .map(|rows| {
            rows.iter()
                .map(|m| build_mention(m, instance_domain))
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let content_emojis = build_emojis(
        &[row.text.as_str(), row.spoiler_text.as_str()],
        enrich.emojis,
        media,
    );

    let card = enrich.cards.get(&status_id).map(|c| build_card(c, media));

    let published_at = row.created_at.and_utc();
    let spoiler = sanitize_text(&row.spoiler_text);
    let fallback_url = format!("https://{instance_domain}/@{}/{}", row.username, row.id);
    let url = row
        .url
        .clone()
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| fallback_url.clone());
    let uri = row
        .uri
        .clone()
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| url.clone());

    let content = format_content(&row.text, &mention_list, &tag_list, instance_domain);

    Status {
        id: status_id.to_string(),
        uri,
        url: Some(url),
        created_at: published_at,
        edited_at: row.edited_at.map(|dt| dt.and_utc()),
        content,
        text: Some(row.text),
        visibility: "public",
        language: row.language,
        sensitive: row.sensitive,
        spoiler_text: spoiler,
        in_reply_to_id: row.in_reply_to_id.map(|i| i.to_string()),
        in_reply_to_account_id: row.in_reply_to_account_id.map(|i| i.to_string()),
        account,
        media_attachments,
        mentions: mention_list,
        tags: tag_list,
        emojis: content_emojis,
        reblog: None,
        reblogs_count: u64::try_from(stat.reblogs).unwrap_or(0),
        favourites_count: u64::try_from(stat.favourites).unwrap_or(0),
        replies_count: u64::try_from(stat.replies).unwrap_or(0),
        quotes_count: u64::try_from(stat.quotes).unwrap_or(0),
        favourited: enrich.viewer.favourited.contains(&status_id),
        reblogged: enrich.viewer.reblogged.contains(&status_id),
        muted: false,
        bookmarked: enrich.viewer.bookmarked.contains(&status_id),
        pinned: false,
        quote: None,
        quote_approval: QuoteApproval::public(),
        poll: None,
        filtered: Vec::new(),
        card,
    }
}

fn build_account(
    row: &BaseRow,
    instance_domain: &str,
    media: &MediaConfig,
    emojis: &HashMap<String, EmojiRow>,
) -> Account {
    let is_local = row.domain.is_none();
    let acct = match &row.domain {
        Some(d) => format!("{}@{}", row.username, d),
        None => row.username.clone(),
    };
    let url = row
        .account_url
        .clone()
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| format!("https://{instance_domain}/@{acct}"));
    let uri = if row.account_uri.is_empty() {
        format!("https://{instance_domain}/users/{}", row.username)
    } else {
        row.account_uri.clone()
    };

    let avatar = media.avatar_url(
        row.account_id,
        row.avatar_file_name.as_deref(),
        row.avatar_remote_url.as_deref(),
        is_local,
    );
    let header = media.header_url(
        row.account_id,
        row.header_file_name.as_deref(),
        non_empty(&row.header_remote_url),
        is_local,
    );

    let bot = matches!(row.actor_type.as_deref(), Some("Service" | "Application"));
    let group = row.actor_type.as_deref() == Some("Group");

    let fields = row
        .fields
        .as_ref()
        .and_then(|v| serde_json::from_value::<Vec<FieldRow>>(v.clone()).ok())
        .map(|rows| {
            rows.into_iter()
                .map(|f| Field {
                    name: sanitize_text(&f.name),
                    value: sanitize_html(&f.value),
                    verified_at: f.verified_at,
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let account_emojis = build_emojis(
        &[row.display_name.as_str(), row.note.as_str()],
        emojis,
        media,
    );

    Account {
        id: row.account_id.to_string(),
        username: row.username.clone(),
        acct,
        url,
        uri,
        display_name: sanitize_text(&row.display_name),
        note: sanitize_html(&row.note),
        avatar: avatar.clone(),
        avatar_static: avatar,
        header: header.clone(),
        header_static: header,
        locked: row.locked,
        bot,
        group,
        discoverable: row.discoverable,
        indexable: row.indexable,
        statuses_count: u64::try_from(row.statuses_count).unwrap_or(0),
        followers_count: u64::try_from(row.followers_count).unwrap_or(0),
        following_count: u64::try_from(row.following_count).unwrap_or(0),
        created_at: row.account_created_at.and_utc(),
        fields,
        emojis: account_emojis,
        last_status_at: row
            .last_status_at
            .map(|dt| dt.date().format("%Y-%m-%d").to_string()),
    }
}

#[derive(Deserialize)]
struct FieldRow {
    #[serde(default)]
    name: String,
    #[serde(default)]
    value: String,
    #[serde(default)]
    verified_at: Option<DateTime<Utc>>,
}

fn build_media_attachment(row: &MediaRow, media: &MediaConfig) -> MediaAttachment {
    let url = media.media_attachment_url(
        row.id,
        row.file_file_name.as_deref(),
        non_empty(&row.remote_url),
        row.account_is_local,
    );
    let preview_url = media
        .media_thumbnail_url(
            row.id,
            row.thumbnail_file_name.as_deref(),
            row.account_is_local,
        )
        .or_else(|| url.clone());
    let (width, height) = file_meta_dimensions(row.file_meta.as_ref());
    let meta = match (width, height) {
        (Some(w), Some(h)) if w > 0 && h > 0 => Some(MediaMeta {
            original: Some(MediaMetaDimensions::new(w, h)),
            small: None,
        }),
        _ => None,
    };

    MediaAttachment {
        id: row.id.to_string(),
        media_type: media_type_str(row.media_type),
        url,
        preview_url,
        remote_url: non_empty(&row.remote_url).map(str::to_owned),
        meta,
        description: row.description.as_deref().map(sanitize_text),
        blurhash: row.blurhash.clone(),
    }
}

fn build_card(row: &CardRow, media: &MediaConfig) -> PreviewCard {
    let image = media.preview_card_image_url(row.id, row.image_file_name.as_deref());
    PreviewCard {
        url: row.url.clone(),
        title: sanitize_text(&row.title),
        description: sanitize_text(&row.description),
        card_type: card_type_str(row.card_type),
        authors: if row.author_name.is_empty() {
            Vec::new()
        } else {
            vec![PreviewCardAuthor {
                name: row.author_name.clone(),
                url: row.author_url.clone(),
                account: None,
            }]
        },
        author_name: sanitize_text(&row.author_name),
        author_url: row.author_url.clone(),
        provider_name: sanitize_text(&row.provider_name),
        provider_url: row.provider_url.clone(),
        html: sanitize_html(&row.html),
        width: row.width,
        height: row.height,
        image,
        image_description: sanitize_text(&row.image_description),
        embed_url: non_empty(&row.embed_url).map(str::to_owned),
        blurhash: row.blurhash.clone(),
        history: Vec::new(),
    }
}

fn build_mention(row: &MentionRow, instance_domain: &str) -> Mention {
    let acct = match &row.domain {
        Some(d) => format!("{}@{}", row.username, d),
        None => row.username.clone(),
    };
    let url = row
        .url
        .clone()
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| format!("https://{instance_domain}/@{acct}"));
    Mention {
        id: row.account_id.to_string(),
        username: row.username.clone(),
        url,
        acct,
    }
}

fn build_emojis(
    texts: &[&str],
    emojis: &HashMap<String, EmojiRow>,
    media: &MediaConfig,
) -> Vec<CustomEmoji> {
    let mut used: HashSet<String> = HashSet::new();
    let mut out: Vec<CustomEmoji> = Vec::new();
    for text in texts {
        for m in shortcode_regex().captures_iter(text) {
            let Some(shortcode) = m.get(1).map(|c| c.as_str()) else {
                continue;
            };
            if used.contains(shortcode) {
                continue;
            }
            let Some(emoji) = emojis.get(shortcode) else {
                continue;
            };
            let is_local = emoji.domain.is_none();
            let Some(url) = media.custom_emoji_url(
                emoji.id,
                emoji.image_file_name.as_deref(),
                emoji.image_remote_url.as_deref(),
                is_local,
            ) else {
                continue;
            };
            out.push(CustomEmoji {
                shortcode: emoji.shortcode.clone(),
                static_url: url.clone(),
                url,
                visible_in_picker: true,
            });
            used.insert(shortcode.to_owned());
        }
    }
    out
}

fn scan_shortcodes(base: &[BaseRow]) -> HashSet<String> {
    let re = shortcode_regex();
    let mut set = HashSet::new();
    for row in base {
        for text in [
            row.text.as_str(),
            row.spoiler_text.as_str(),
            row.display_name.as_str(),
            row.note.as_str(),
        ] {
            for m in re.captures_iter(text) {
                if let Some(c) = m.get(1) {
                    set.insert(c.as_str().to_owned());
                }
            }
        }
    }
    set
}

fn shortcode_regex() -> &'static Regex {
    use std::sync::OnceLock;
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r":([a-zA-Z0-9_]{2,}):").expect("valid regex"))
}

fn non_empty(s: &str) -> Option<&str> {
    if s.is_empty() { None } else { Some(s) }
}

fn media_type_str(kind: i32) -> String {
    match kind {
        0 => "image",
        1 => "gifv",
        2 => "video",
        4 => "audio",
        _ => "unknown",
    }
    .to_owned()
}

fn card_type_str(kind: i32) -> String {
    match kind {
        1 => "photo",
        2 => "video",
        3 => "rich",
        _ => "link",
    }
    .to_owned()
}

fn file_meta_dimensions(meta: Option<&serde_json::Value>) -> (Option<u32>, Option<u32>) {
    let Some(meta) = meta else {
        return (None, None);
    };
    let original = meta.get("original");
    let width = original
        .and_then(|v| v.get("width"))
        .and_then(serde_json::Value::as_u64)
        .and_then(|n| u32::try_from(n).ok());
    let height = original
        .and_then(|v| v.get("height"))
        .and_then(serde_json::Value::as_u64)
        .and_then(|n| u32::try_from(n).ok());
    (width, height)
}

fn format_content(text: &str, mentions: &[Mention], tags: &[Tag], instance_domain: &str) -> String {
    let mut spans: Vec<(usize, usize, String)> = Vec::new();

    for m in url_regex().find_iter(text) {
        let url = m.as_str();
        spans.push((
            m.start(),
            m.end(),
            format!(
                "<a href=\"{url}\" rel=\"nofollow noopener\">{url}</a>",
                url = escape_attr(url)
            ),
        ));
    }

    for mention in mentions {
        let anchor = mention_anchor(mention);
        if let Some(domain) = mention.acct.split('@').nth(1) {
            let needle = format!("@{}@{domain}", mention.username);
            push_word_matches(text, &needle, &anchor, &mut spans);
        }
        let needle = format!("@{}", mention.username);
        push_word_matches(text, &needle, &anchor, &mut spans);
    }

    for tag in tags {
        let needle = format!("#{}", tag.name);
        let anchor = tag_anchor(tag, instance_domain);
        push_word_matches(text, &needle, &anchor, &mut spans);
    }

    spans.sort_by_key(|(start, end, _)| (*start, std::cmp::Reverse(*end)));
    let mut non_overlapping: Vec<(usize, usize, String)> = Vec::with_capacity(spans.len());
    for span in spans {
        if non_overlapping.last().is_none_or(|last| span.0 >= last.1) {
            non_overlapping.push(span);
        }
    }

    let mut out = String::with_capacity(text.len() + 32);
    let mut cursor = 0;
    for (start, end, anchor) in non_overlapping {
        out.push_str(&escape_text(&text[cursor..start]));
        out.push_str(&anchor);
        cursor = end;
    }
    out.push_str(&escape_text(&text[cursor..]));

    let paragraphs: Vec<String> = out
        .split("\n\n")
        .filter(|p| !p.is_empty())
        .map(|p| format!("<p>{}</p>", p.replace('\n', "<br />")))
        .collect();
    if paragraphs.is_empty() {
        "<p></p>".to_owned()
    } else {
        paragraphs.join("")
    }
}

fn push_word_matches(
    text: &str,
    needle: &str,
    anchor: &str,
    spans: &mut Vec<(usize, usize, String)>,
) {
    if needle.len() < 2 {
        return;
    }
    let mut search_from = 0;
    while let Some(rel) = text[search_from..].find(needle) {
        let start = search_from + rel;
        let end = start + needle.len();
        let preceded_by_word = start > 0
            && text[..start]
                .chars()
                .next_back()
                .is_some_and(|c| c.is_alphanumeric() || c == '_' || c == '@' || c == '#');
        let followed_by_word = text[end..]
            .chars()
            .next()
            .is_some_and(|c| c.is_alphanumeric() || c == '_' || c == '@');
        if !preceded_by_word && !followed_by_word {
            spans.push((start, end, anchor.to_owned()));
        }
        search_from = end;
    }
}

fn mention_anchor(m: &Mention) -> String {
    format!(
        "<a href=\"{url}\" class=\"u-url mention\">@<span>{user}</span></a>",
        url = escape_attr(&m.url),
        user = escape_text(&m.username),
    )
}

fn tag_anchor(t: &Tag, instance_domain: &str) -> String {
    format!(
        "<a href=\"https://{instance_domain}/tags/{name}\" class=\"mention hashtag\" rel=\"tag\">#<span>{display}</span></a>",
        name = escape_attr(&t.name),
        display = escape_text(&t.name),
    )
}

fn url_regex() -> &'static Regex {
    use std::sync::OnceLock;
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"https?://[^\s<>\x22\]]+").expect("valid regex"))
}

fn escape_text(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            _ => out.push(c),
        }
    }
    out
}

fn escape_attr(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            _ => out.push(c),
        }
    }
    out
}
