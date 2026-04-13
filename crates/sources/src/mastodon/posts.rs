use async_trait::async_trait;
use chrono::{DateTime, Utc};
use common::types::{Author, Engagement, Post};
use feed::candidate::Candidate;
use feed::source::Source;
use sqlx::{FromRow, PgPool};

#[derive(FromRow)]
struct StatusRow {
    id: i64,
    uri: String,
    url: Option<String>,
    text: String,
    spoiler_text: Option<String>,
    sensitive: bool,
    language: Option<String>,
    created_at: DateTime<Utc>,
    username: String,
    domain: Option<String>,
    display_name: Option<String>,
    account_url: Option<String>,
}

fn row_to_post(row: StatusRow, instance_domain: &str) -> Post {
    let handle = match &row.domain {
        Some(d) => format!("{}@{}", row.username, d),
        None => format!("{}@{}", row.username, instance_domain),
    };
    let author_url = row
        .account_url
        .unwrap_or_else(|| format!("https://{}/@{}", instance_domain, row.username));
    let url = row.url.clone().unwrap_or_else(|| row.uri.clone());
    let content_warning = row.spoiler_text.filter(|s| !s.is_empty());

    Post {
        provider_id: Some(row.id),
        provider_domain: Some(instance_domain.to_string()),
        url,
        uri: Some(row.uri),
        content: row.text.clone(),
        text: row.text,
        author: Author {
            handle,
            display_name: row.display_name.unwrap_or_default(),
            url: author_url,
            avatar_url: None,
            emojis: Vec::new(),
        },
        published_at: row.created_at,
        language: row.language,
        sensitive: row.sensitive,
        content_warning,
        media: Vec::new(),
        engagement: Engagement::default(),
        link: None,
        reply_to: None,
        quote: None,
        tags: Vec::new(),
        emojis: Vec::new(),
    }
}

const NATIVE_TAG_QUERY: &str = r"
    SELECT
        s.id,
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
        a.url AS account_url
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
        a.url AS account_url
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
}

impl NativeTagSource {
    #[must_use]
    pub fn new(db: PgPool, tag: String, instance_domain: String) -> Self {
        Self {
            db,
            tag,
            instance_domain,
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
                    let post = row_to_post(r, &self.instance_domain);
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
}

impl FederatedTagSource {
    #[must_use]
    pub fn new(db: PgPool, tag: String, instance_domain: String) -> Self {
        Self {
            db,
            tag,
            instance_domain,
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
                    let post = row_to_post(r, &self.instance_domain);
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

#[cfg(test)]
mod tests {
    use super::*;

    fn native_row() -> StatusRow {
        StatusRow {
            id: 42,
            uri: "https://local.test/users/alice/statuses/42".into(),
            url: Some("https://local.test/@alice/42".into()),
            text: "<p>native hello</p>".into(),
            spoiler_text: None,
            sensitive: false,
            language: Some("en".into()),
            created_at: chrono::DateTime::parse_from_rfc3339("2026-04-13T12:00:00Z")
                .unwrap()
                .with_timezone(&chrono::Utc),
            username: "alice".into(),
            domain: None,
            display_name: Some("Alice".into()),
            account_url: Some("https://local.test/@alice".into()),
        }
    }

    fn federated_row() -> StatusRow {
        StatusRow {
            id: 99,
            uri: "https://remote.example/users/bob/statuses/99".into(),
            url: None,
            text: "<p>federated hello</p>".into(),
            spoiler_text: Some("cw text".into()),
            sensitive: true,
            language: None,
            created_at: chrono::DateTime::parse_from_rfc3339("2026-04-13T12:00:00Z")
                .unwrap()
                .with_timezone(&chrono::Utc),
            username: "bob".into(),
            domain: Some("remote.example".into()),
            display_name: None,
            account_url: None,
        }
    }

    #[test]
    fn row_to_post_tags_native_with_instance_domain() {
        let post = row_to_post(native_row(), "local.test");
        assert_eq!(post.provider_domain.as_deref(), Some("local.test"));
        assert_eq!(post.provider_id, Some(42));
    }

    #[test]
    fn row_to_post_builds_native_handle_with_instance_domain() {
        let post = row_to_post(native_row(), "local.test");
        assert_eq!(post.author.handle, "alice@local.test");
    }

    #[test]
    fn row_to_post_builds_federated_handle_with_remote_domain() {
        let post = row_to_post(federated_row(), "local.test");
        assert_eq!(post.author.handle, "bob@remote.example");
    }

    #[test]
    fn row_to_post_federated_still_tags_provider_as_instance() {
        let post = row_to_post(federated_row(), "local.test");
        assert_eq!(
            post.provider_domain.as_deref(),
            Some("local.test"),
            "federated rows are still owned by this instance's DB — provider_domain tracks storage, not authorship"
        );
    }

    #[test]
    fn row_to_post_url_falls_back_to_uri_when_null() {
        let post = row_to_post(federated_row(), "local.test");
        assert_eq!(post.url, "https://remote.example/users/bob/statuses/99");
    }

    #[test]
    fn row_to_post_prefers_explicit_url_when_present() {
        let post = row_to_post(native_row(), "local.test");
        assert_eq!(post.url, "https://local.test/@alice/42");
    }

    #[test]
    fn row_to_post_empty_spoiler_becomes_none() {
        let mut row = native_row();
        row.spoiler_text = Some(String::new());
        let post = row_to_post(row, "local.test");
        assert!(post.content_warning.is_none());
    }

    #[test]
    fn row_to_post_nonempty_spoiler_becomes_content_warning() {
        let post = row_to_post(federated_row(), "local.test");
        assert_eq!(post.content_warning.as_deref(), Some("cw text"));
    }

    #[test]
    fn row_to_post_missing_display_name_defaults_to_empty() {
        let post = row_to_post(federated_row(), "local.test");
        assert_eq!(post.author.display_name, "");
    }

    #[test]
    fn row_to_post_missing_account_url_constructs_from_instance_domain() {
        let post = row_to_post(federated_row(), "local.test");
        assert_eq!(post.author.url, "https://local.test/@bob");
    }

    #[test]
    fn row_to_post_preserves_sensitive_and_language() {
        let post = row_to_post(native_row(), "local.test");
        assert!(!post.sensitive);
        assert_eq!(post.language.as_deref(), Some("en"));
    }

    #[test]
    fn row_to_post_preserves_published_at() {
        let post = row_to_post(native_row(), "local.test");
        assert_eq!(post.published_at.to_rfc3339(), "2026-04-13T12:00:00+00:00");
    }
}
