use async_trait::async_trait;
use common::types::Post;
use feed::candidate::Candidate;
use feed::source::Source;
use sqlx::PgPool;

use common::paperclip::MediaConfig;

use crate::mastodon::row::{StatusRow, row_to_post};

const NATIVE_TAG_QUERY: &str = r"
    SELECT
        s.id,
        s.account_id,
        s.uri,
        COALESCE(s.url, s.uri) AS url,
        s.text,
        s.spoiler_text,
        s.sensitive,
        s.language,
        s.created_at,
        a.username,
        a.domain,
        a.display_name,
        a.url AS account_url,
        a.avatar_file_name,
        a.avatar_remote_url,
        a.header_file_name,
        a.header_remote_url
    FROM statuses s
    JOIN accounts a ON a.id = s.account_id
    JOIN statuses_tags st ON st.status_id = s.id
    JOIN tags t ON t.id = st.tag_id
    WHERE LOWER(t.name) = LOWER($1)
      AND s.visibility IN (0, 1)
      AND s.reblog_of_id IS NULL
      AND a.domain IS NULL
    ORDER BY s.created_at DESC
    LIMIT $2
";

const FEDERATED_TAG_QUERY: &str = r"
    SELECT
        s.id,
        s.account_id,
        s.uri,
        COALESCE(s.url, s.uri) AS url,
        s.text,
        s.spoiler_text,
        s.sensitive,
        s.language,
        s.created_at,
        a.username,
        a.domain,
        a.display_name,
        a.url AS account_url,
        a.avatar_file_name,
        a.avatar_remote_url,
        a.header_file_name,
        a.header_remote_url
    FROM statuses s
    JOIN accounts a ON a.id = s.account_id
    JOIN statuses_tags st ON st.status_id = s.id
    JOIN tags t ON t.id = st.tag_id
    WHERE LOWER(t.name) = LOWER($1)
      AND s.visibility IN (0, 1)
      AND s.reblog_of_id IS NULL
      AND a.domain IS NOT NULL
    ORDER BY s.created_at DESC
    LIMIT $2
";

pub struct NativeTagSource {
    db: PgPool,
    tag: String,
    instance_domain: String,
    media: MediaConfig,
}

impl NativeTagSource {
    #[must_use]
    pub fn new(db: PgPool, tag: String, instance_domain: String, media: MediaConfig) -> Self {
        Self {
            db,
            tag,
            instance_domain,
            media,
        }
    }
}

#[async_trait]
impl Source<Post> for NativeTagSource {
    fn name(&self) -> &'static str {
        "local/tag/native"
    }

    async fn collect(&self, limit: usize) -> Vec<Candidate<Post>> {
        let rows = sqlx::query_as::<_, StatusRow>(NATIVE_TAG_QUERY)
            .bind(&self.tag)
            .bind(i64::try_from(limit).unwrap_or(i64::MAX))
            .fetch_all(&self.db)
            .await;

        match rows {
            Ok(rows) => rows
                .into_iter()
                .map(|r| {
                    let post = row_to_post(r, &self.instance_domain, &self.media);
                    Candidate::new(post, "local/tag/native")
                })
                .collect(),
            Err(e) => {
                tracing::warn!(error = %e, tag = %self.tag, "native tag source query failed");
                Vec::new()
            }
        }
    }
}

pub struct FederatedTagSource {
    db: PgPool,
    tag: String,
    instance_domain: String,
    media: MediaConfig,
}

impl FederatedTagSource {
    #[must_use]
    pub fn new(db: PgPool, tag: String, instance_domain: String, media: MediaConfig) -> Self {
        Self {
            db,
            tag,
            instance_domain,
            media,
        }
    }
}

#[async_trait]
impl Source<Post> for FederatedTagSource {
    fn name(&self) -> &'static str {
        "local/tag/federated"
    }

    async fn collect(&self, limit: usize) -> Vec<Candidate<Post>> {
        let rows = sqlx::query_as::<_, StatusRow>(FEDERATED_TAG_QUERY)
            .bind(&self.tag)
            .bind(i64::try_from(limit).unwrap_or(i64::MAX))
            .fetch_all(&self.db)
            .await;

        match rows {
            Ok(rows) => rows
                .into_iter()
                .map(|r| {
                    let post = row_to_post(r, &self.instance_domain, &self.media);
                    Candidate::new(post, "local/tag/federated")
                })
                .collect(),
            Err(e) => {
                tracing::warn!(error = %e, tag = %self.tag, "federated tag source query failed");
                Vec::new()
            }
        }
    }
}
