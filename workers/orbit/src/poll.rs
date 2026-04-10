use chrono::NaiveDateTime;
use sqlx::PgPool;

use crate::engagement::{EngagementKind, RawEngagement, TargetPost};

#[derive(sqlx::FromRow)]
struct EngagementRow {
    id: i64,
    account_id: i64,
    created_at: NaiveDateTime,
    target_text: String,
    spoiler_text: String,
    author_name: String,
    author_handle: String,
    alt_texts: Vec<String>,
    tags: Vec<String>,
}

impl EngagementRow {
    fn into_engagement(self, kind: EngagementKind) -> RawEngagement {
        RawEngagement {
            id: self.id,
            account_id: self.account_id,
            created_at: self.created_at,
            kind,
            target: TargetPost {
                text: self.target_text,
                spoiler_text: self.spoiler_text,
                author_name: self.author_name,
                author_handle: self.author_handle,
                alt_texts: self.alt_texts,
                tags: self.tags,
            },
        }
    }
}

pub async fn poll_favourites(
    db: &PgPool,
    cursor: i64,
    batch_size: i64,
    instance_domain: &str,
) -> anyhow::Result<Vec<RawEngagement>> {
    let rows = sqlx::query_as::<_, EngagementRow>(
        "SELECT
            f.id,
            f.account_id,
            f.created_at,
            s.text AS target_text,
            s.spoiler_text,
            author.display_name AS author_name,
            author.username || '@' || COALESCE(author.domain, $3) AS author_handle,
            COALESCE(
                array_agg(DISTINCT ma.description) FILTER (WHERE ma.description IS NOT NULL AND ma.description != ''),
                '{}'
            ) AS alt_texts,
            COALESCE(
                array_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL),
                '{}'
            ) AS tags
        FROM favourites f
        JOIN accounts actor ON actor.id = f.account_id AND actor.domain IS NULL
        JOIN statuses s ON s.id = f.status_id
        JOIN accounts author ON author.id = s.account_id
        LEFT JOIN media_attachments ma ON ma.status_id = s.id
        LEFT JOIN statuses_tags st ON st.status_id = s.id
        LEFT JOIN tags t ON t.id = st.tag_id
        WHERE f.id > $1
        GROUP BY f.id, f.account_id, f.created_at, s.text, s.spoiler_text,
                 author.display_name, author.username, author.domain
        ORDER BY f.id ASC
        LIMIT $2",
    )
    .bind(cursor)
    .bind(batch_size)
    .bind(instance_domain)
    .fetch_all(db)
    .await?;

    Ok(rows
        .into_iter()
        .map(|r| r.into_engagement(EngagementKind::Like))
        .collect())
}

pub async fn poll_reblogs(
    db: &PgPool,
    cursor: i64,
    batch_size: i64,
    instance_domain: &str,
) -> anyhow::Result<Vec<RawEngagement>> {
    let rows = sqlx::query_as::<_, EngagementRow>(
        "SELECT
            s.id,
            s.account_id,
            s.created_at,
            target.text AS target_text,
            target.spoiler_text,
            author.display_name AS author_name,
            author.username || '@' || COALESCE(author.domain, $3) AS author_handle,
            COALESCE(
                array_agg(DISTINCT ma.description) FILTER (WHERE ma.description IS NOT NULL AND ma.description != ''),
                '{}'
            ) AS alt_texts,
            COALESCE(
                array_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL),
                '{}'
            ) AS tags
        FROM statuses s
        JOIN accounts actor ON actor.id = s.account_id AND actor.domain IS NULL
        JOIN statuses target ON target.id = s.reblog_of_id
        JOIN accounts author ON author.id = target.account_id
        LEFT JOIN media_attachments ma ON ma.status_id = target.id
        LEFT JOIN statuses_tags st ON st.status_id = target.id
        LEFT JOIN tags t ON t.id = st.tag_id
        WHERE s.reblog_of_id IS NOT NULL
          AND s.id > $1
        GROUP BY s.id, s.account_id, s.created_at, target.text, target.spoiler_text,
                 author.display_name, author.username, author.domain
        ORDER BY s.id ASC
        LIMIT $2",
    )
    .bind(cursor)
    .bind(batch_size)
    .bind(instance_domain)
    .fetch_all(db)
    .await?;

    Ok(rows
        .into_iter()
        .map(|r| r.into_engagement(EngagementKind::Repost))
        .collect())
}

pub async fn poll_replies(
    db: &PgPool,
    cursor: i64,
    batch_size: i64,
    instance_domain: &str,
) -> anyhow::Result<Vec<RawEngagement>> {
    let rows = sqlx::query_as::<_, EngagementRow>(
        "SELECT
            s.id,
            s.account_id,
            s.created_at,
            parent.text AS target_text,
            parent.spoiler_text,
            author.display_name AS author_name,
            author.username || '@' || COALESCE(author.domain, $3) AS author_handle,
            COALESCE(
                array_agg(DISTINCT ma.description) FILTER (WHERE ma.description IS NOT NULL AND ma.description != ''),
                '{}'
            ) AS alt_texts,
            COALESCE(
                array_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL),
                '{}'
            ) AS tags
        FROM statuses s
        JOIN accounts actor ON actor.id = s.account_id AND actor.domain IS NULL
        JOIN statuses parent ON parent.id = s.in_reply_to_id
        JOIN accounts author ON author.id = parent.account_id
        LEFT JOIN media_attachments ma ON ma.status_id = parent.id
        LEFT JOIN statuses_tags st ON st.status_id = parent.id
        LEFT JOIN tags t ON t.id = st.tag_id
        WHERE s.in_reply_to_id IS NOT NULL
          AND s.reblog_of_id IS NULL
          AND s.id > $1
        GROUP BY s.id, s.account_id, s.created_at, parent.text, parent.spoiler_text,
                 author.display_name, author.username, author.domain
        ORDER BY s.id ASC
        LIMIT $2",
    )
    .bind(cursor)
    .bind(batch_size)
    .bind(instance_domain)
    .fetch_all(db)
    .await?;

    Ok(rows
        .into_iter()
        .map(|r| r.into_engagement(EngagementKind::Reply))
        .collect())
}

pub async fn load_cursor(db: &PgPool, source: &str) -> i64 {
    sqlx::query_scalar::<_, i64>("SELECT last_id FROM orbit_cursors WHERE source_name = $1")
        .bind(source)
        .fetch_optional(db)
        .await
        .ok()
        .flatten()
        .unwrap_or(0)
}

pub async fn save_cursor(db: &PgPool, source: &str, last_id: i64) {
    if let Err(e) = sqlx::query(
        "INSERT INTO orbit_cursors (source_name, last_id, updated_at)
         VALUES ($1, $2, now())
         ON CONFLICT (source_name) DO UPDATE SET
             last_id = EXCLUDED.last_id,
             updated_at = now()",
    )
    .bind(source)
    .bind(last_id)
    .execute(db)
    .await
    {
        tracing::warn!(source_name = source, error = %e, "failed to save cursor");
        metrics::counter!("fediway_orbit_cursor_save_errors_total").increment(1);
    }
}

/// Initialize cursor for first startup by finding the start of the replay window.
/// Returns the ID just before the first engagement within the last `replay_hours`,
/// so the first poll picks up all recent activity without replaying years of history.
pub async fn init_cursor(db: &PgPool, kind: EngagementKind, replay_hours: u64) -> i64 {
    if replay_hours == 0 {
        return 0;
    }

    // Table name can't be parameterized in SQL, but the match on EngagementKind
    // ensures only known table names are used. Hours are bound via make_interval.
    let query = match kind {
        EngagementKind::Like => {
            "SELECT COALESCE(MIN(id) - 1, 0) FROM favourites WHERE created_at >= now() - make_interval(hours => $1)"
        }
        EngagementKind::Repost | EngagementKind::Reply => {
            "SELECT COALESCE(MIN(id) - 1, 0) FROM statuses WHERE created_at >= now() - make_interval(hours => $1)"
        }
    };

    #[allow(clippy::cast_possible_wrap)]
    let hours = replay_hours as i32;

    sqlx::query_scalar::<_, i64>(query)
        .bind(hours)
        .fetch_one(db)
        .await
        .unwrap_or(0)
}
