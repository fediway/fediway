use chrono::NaiveDateTime;
use common::types::{Author, Engagement, Post};
use sqlx::FromRow;

use common::paperclip::MediaConfig;

#[derive(FromRow)]
pub(crate) struct StatusRow {
    pub id: i64,
    pub account_id: i64,
    pub uri: String,
    pub url: Option<String>,
    pub text: String,
    pub spoiler_text: Option<String>,
    pub sensitive: bool,
    pub language: Option<String>,
    pub created_at: NaiveDateTime,
    pub username: String,
    pub domain: Option<String>,
    pub display_name: Option<String>,
    pub account_url: Option<String>,
    pub avatar_file_name: Option<String>,
    pub avatar_remote_url: Option<String>,
    pub header_file_name: Option<String>,
    pub header_remote_url: Option<String>,
    pub avatar_storage_schema_version: Option<i32>,
    pub header_storage_schema_version: Option<i32>,
}

pub(crate) fn row_to_post(row: StatusRow, instance_domain: &str, media: &MediaConfig) -> Post {
    let handle = match &row.domain {
        Some(d) => format!("{}@{}", row.username, d),
        None => format!("{}@{}", row.username, instance_domain),
    };
    let author_url = row
        .account_url
        .unwrap_or_else(|| format!("https://{}/@{}", instance_domain, row.username));
    let url = row.url.clone().unwrap_or_else(|| row.uri.clone());
    let content_warning = row.spoiler_text.filter(|s| !s.is_empty());
    let is_remote = row.domain.is_some();
    let avatar_cached = is_remote && row.avatar_storage_schema_version.unwrap_or(0) >= 1;
    let header_cached = is_remote && row.header_storage_schema_version.unwrap_or(0) >= 1;
    let avatar_url = media.avatar_url(
        row.account_id,
        row.avatar_file_name.as_deref(),
        row.avatar_remote_url.as_deref(),
        avatar_cached,
    );
    let header_url = media.header_url(
        row.account_id,
        row.header_file_name.as_deref(),
        row.header_remote_url.as_deref(),
        header_cached,
    );

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
            avatar_url: Some(avatar_url),
            header_url: Some(header_url),
            emojis: Vec::new(),
        },
        published_at: row.created_at.and_utc(),
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

#[cfg(test)]
mod tests {
    use super::*;

    fn media() -> MediaConfig {
        MediaConfig::new("local.test".into(), false)
    }

    fn native_row() -> StatusRow {
        StatusRow {
            id: 42,
            account_id: 7,
            uri: "https://local.test/users/alice/statuses/42".into(),
            url: Some("https://local.test/@alice/42".into()),
            text: "<p>native hello</p>".into(),
            spoiler_text: None,
            sensitive: false,
            language: Some("en".into()),
            created_at: chrono::NaiveDateTime::parse_from_str(
                "2026-04-13T12:00:00",
                "%Y-%m-%dT%H:%M:%S",
            )
            .unwrap(),
            username: "alice".into(),
            domain: None,
            display_name: Some("Alice".into()),
            account_url: Some("https://local.test/@alice".into()),
            avatar_file_name: None,
            avatar_remote_url: None,
            header_file_name: None,
            header_remote_url: None,
            avatar_storage_schema_version: None,
            header_storage_schema_version: None,
        }
    }

    fn federated_row() -> StatusRow {
        StatusRow {
            id: 99,
            account_id: 8,
            uri: "https://remote.example/users/bob/statuses/99".into(),
            url: None,
            text: "<p>federated hello</p>".into(),
            spoiler_text: Some("cw text".into()),
            sensitive: true,
            language: None,
            created_at: chrono::NaiveDateTime::parse_from_str(
                "2026-04-13T12:00:00",
                "%Y-%m-%dT%H:%M:%S",
            )
            .unwrap(),
            username: "bob".into(),
            domain: Some("remote.example".into()),
            display_name: None,
            account_url: None,
            avatar_file_name: None,
            avatar_remote_url: None,
            header_file_name: None,
            header_remote_url: None,
            avatar_storage_schema_version: None,
            header_storage_schema_version: None,
        }
    }

    #[test]
    fn tags_native_with_instance_domain() {
        let post = row_to_post(native_row(), "local.test", &media());
        assert_eq!(post.provider_domain.as_deref(), Some("local.test"));
        assert_eq!(post.provider_id, Some(42));
    }

    #[test]
    fn builds_native_handle_with_instance_domain() {
        let post = row_to_post(native_row(), "local.test", &media());
        assert_eq!(post.author.handle, "alice@local.test");
    }

    #[test]
    fn builds_federated_handle_with_remote_domain() {
        let post = row_to_post(federated_row(), "local.test", &media());
        assert_eq!(post.author.handle, "bob@remote.example");
    }

    #[test]
    fn federated_still_tags_provider_as_instance() {
        let post = row_to_post(federated_row(), "local.test", &media());
        assert_eq!(post.provider_domain.as_deref(), Some("local.test"));
    }

    #[test]
    fn url_falls_back_to_uri_when_null() {
        let post = row_to_post(federated_row(), "local.test", &media());
        assert_eq!(post.url, "https://remote.example/users/bob/statuses/99");
    }

    #[test]
    fn prefers_explicit_url_when_present() {
        let post = row_to_post(native_row(), "local.test", &media());
        assert_eq!(post.url, "https://local.test/@alice/42");
    }

    #[test]
    fn empty_spoiler_becomes_none() {
        let mut row = native_row();
        row.spoiler_text = Some(String::new());
        let post = row_to_post(row, "local.test", &media());
        assert!(post.content_warning.is_none());
    }

    #[test]
    fn nonempty_spoiler_becomes_content_warning() {
        let post = row_to_post(federated_row(), "local.test", &media());
        assert_eq!(post.content_warning.as_deref(), Some("cw text"));
    }

    #[test]
    fn missing_display_name_defaults_to_empty() {
        let post = row_to_post(federated_row(), "local.test", &media());
        assert_eq!(post.author.display_name, "");
    }

    #[test]
    fn missing_account_url_constructs_from_instance_domain() {
        let post = row_to_post(federated_row(), "local.test", &media());
        assert_eq!(post.author.url, "https://local.test/@bob");
    }

    #[test]
    fn preserves_sensitive_and_language() {
        let post = row_to_post(native_row(), "local.test", &media());
        assert!(!post.sensitive);
        assert_eq!(post.language.as_deref(), Some("en"));
    }

    #[test]
    fn preserves_published_at() {
        let post = row_to_post(native_row(), "local.test", &media());
        assert_eq!(post.published_at.to_rfc3339(), "2026-04-13T12:00:00+00:00");
    }

    #[test]
    fn missing_avatar_returns_full_url() {
        let post = row_to_post(native_row(), "local.test", &media());
        assert_eq!(
            post.author.avatar_url.as_deref(),
            Some("https://local.test/avatars/original/missing.png")
        );
    }

    #[test]
    fn uploaded_avatar_uses_paperclip_path() {
        let mut row = native_row();
        row.avatar_file_name = Some("abc.jpg".into());
        let post = row_to_post(row, "local.test", &media());
        assert_eq!(
            post.author.avatar_url.as_deref(),
            Some("https://local.test/system/accounts/avatars/000/000/007/original/abc.jpg")
        );
    }

    #[test]
    fn missing_header_returns_full_url() {
        let post = row_to_post(native_row(), "local.test", &media());
        assert_eq!(
            post.author.header_url.as_deref(),
            Some("https://local.test/headers/original/missing.png")
        );
    }
}
