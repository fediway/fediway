use chrono::{DateTime, Utc};
use sqlx::{FromRow, PgPool};

#[derive(Debug, FromRow)]
pub struct CachedStatus {
    pub id: i64,
    pub provider_domain: String,
    pub remote_id: i64,
    pub post_url: String,
    pub post_uri: String,
    pub post_data: serde_json::Value,
    pub cached_at: DateTime<Utc>,
}

impl CachedStatus {
    #[must_use]
    pub fn is_stale(&self, ttl: std::time::Duration) -> bool {
        let age = Utc::now() - self.cached_at;
        age > chrono::Duration::from_std(ttl).unwrap_or(chrono::Duration::hours(1))
    }
}

/// On conflict (same provider + `remote_id`), updates cached data and returns existing ID.
#[allow(clippy::similar_names)]
pub async fn map_post(
    db: &PgPool,
    provider_domain: &str,
    remote_id: i64,
    post_url: &str,
    post_uri: &str,
    post_data: &serde_json::Value,
) -> Result<i64, sqlx::Error> {
    sqlx::query_scalar::<_, i64>(
        r"INSERT INTO commonfeed_statuses (provider_domain, remote_id, post_url, post_uri, post_data)
          VALUES ($1, $2, $3, $4, $5)
          ON CONFLICT (provider_domain, remote_id) DO UPDATE
              SET post_data = EXCLUDED.post_data,
                  cached_at = NOW()
          RETURNING id",
    )
    .bind(provider_domain)
    .bind(remote_id)
    .bind(post_url)
    .bind(post_uri)
    .bind(post_data)
    .fetch_one(db)
    .await
}

pub struct PostMapping<'a> {
    pub provider_domain: &'a str,
    pub remote_id: i64,
    pub post_url: &'a str,
    pub post_uri: &'a str,
    pub post_data: &'a serde_json::Value,
}

/// Batch upsert: maps multiple posts to snowflake IDs in a single query.
/// Returns a map from `(provider_domain, remote_id)` to snowflake ID.
#[allow(clippy::similar_names)]
pub async fn map_posts(
    db: &PgPool,
    posts: &[PostMapping<'_>],
) -> Result<std::collections::HashMap<(String, i64), i64>, sqlx::Error> {
    if posts.is_empty() {
        return Ok(std::collections::HashMap::new());
    }

    let domains: Vec<&str> = posts.iter().map(|p| p.provider_domain).collect();
    let remote_ids: Vec<i64> = posts.iter().map(|p| p.remote_id).collect();
    let urls: Vec<&str> = posts.iter().map(|p| p.post_url).collect();
    let uris: Vec<&str> = posts.iter().map(|p| p.post_uri).collect();
    let data: Vec<&serde_json::Value> = posts.iter().map(|p| p.post_data).collect();

    let rows = sqlx::query_as::<_, (String, i64, i64)>(
        r"INSERT INTO commonfeed_statuses (provider_domain, remote_id, post_url, post_uri, post_data)
          SELECT * FROM UNNEST($1::text[], $2::bigint[], $3::text[], $4::text[], $5::jsonb[])
          ON CONFLICT (provider_domain, remote_id) DO UPDATE
              SET post_data = EXCLUDED.post_data,
                  cached_at = NOW()
          RETURNING provider_domain, remote_id, id",
    )
    .bind(&domains)
    .bind(&remote_ids)
    .bind(&urls)
    .bind(&uris)
    .bind(&data)
    .fetch_all(db)
    .await?;

    Ok(rows
        .into_iter()
        .map(|(domain, remote_id, id)| ((domain, remote_id), id))
        .collect())
}

pub async fn find_by_id(db: &PgPool, id: i64) -> Result<Option<CachedStatus>, sqlx::Error> {
    sqlx::query_as::<_, CachedStatus>(
        "SELECT id, provider_domain, remote_id, post_url, post_uri, post_data, cached_at
         FROM commonfeed_statuses
         WHERE id = $1",
    )
    .bind(id)
    .fetch_optional(db)
    .await
}

pub async fn update_cache(
    db: &PgPool,
    id: i64,
    post_data: &serde_json::Value,
) -> Result<(), sqlx::Error> {
    sqlx::query("UPDATE commonfeed_statuses SET post_data = $1, cached_at = NOW() WHERE id = $2")
        .bind(post_data)
        .bind(id)
        .execute(db)
        .await?;
    Ok(())
}

pub async fn delete(db: &PgPool, id: i64) -> Result<(), sqlx::Error> {
    sqlx::query("DELETE FROM commonfeed_statuses WHERE id = $1")
        .bind(id)
        .execute(db)
        .await?;
    Ok(())
}
