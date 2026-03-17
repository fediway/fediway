use chrono::{DateTime, Utc};
use common::types::Post;
use serde::Serialize;

use crate::account::{Account, CustomEmoji};
use crate::media_attachment::{MediaAttachment, normalize_media_type};
use crate::mention::Mention;
use crate::tag::Tag;

const MISSING_AVATAR: &str = "/avatars/original/missing.png";
const MISSING_HEADER: &str = "/headers/original/missing.png";

/// Mastodon-compatible Status entity.
/// See: <https://docs.joinmastodon.org/entities/Status/>
#[derive(Debug, Serialize)]
#[allow(clippy::struct_excessive_bools)]
pub struct Status {
    pub id: String,
    pub uri: String,
    pub url: Option<String>,
    pub created_at: DateTime<Utc>,
    pub edited_at: Option<DateTime<Utc>>,
    pub content: String,
    pub text: Option<String>,
    pub visibility: &'static str,
    pub language: Option<String>,
    pub sensitive: bool,
    pub spoiler_text: String,
    pub in_reply_to_id: Option<String>,
    pub in_reply_to_account_id: Option<String>,
    pub account: Account,
    pub media_attachments: Vec<MediaAttachment>,
    pub mentions: Vec<Mention>,
    pub tags: Vec<Tag>,
    pub emojis: Vec<CustomEmoji>,
    pub reblog: Option<Box<Status>>,
    pub reblogs_count: u64,
    pub favourites_count: u64,
    pub replies_count: u64,
    pub quotes_count: u64,
    pub favourited: bool,
    pub reblogged: bool,
    pub muted: bool,
    pub bookmarked: bool,
    pub pinned: bool,
    pub poll: Option<()>,
    pub filtered: Vec<()>,
    pub card: Option<()>,
}

impl From<Post> for Status {
    fn from(post: Post) -> Self {
        let acct = post.author.handle.trim_start_matches('@').to_string();
        let username = acct.split('@').next().unwrap_or(&acct).to_string();

        let avatar = post
            .author
            .avatar_url
            .unwrap_or_else(|| MISSING_AVATAR.to_string());

        let media_attachments: Vec<MediaAttachment> = post
            .media
            .iter()
            .enumerate()
            .map(|(i, m)| MediaAttachment {
                id: format!("media_{i}"),
                media_type: normalize_media_type(&m.media_type),
                url: Some(m.url.clone()),
                preview_url: m.thumbnail_url.clone(),
                remote_url: None,
                meta: None,
                description: m.alt.clone(),
                blurhash: m.blurhash.clone(),
            })
            .collect();

        Self {
            id: post.url.clone(),
            uri: post.url.clone(),
            url: Some(post.url),
            created_at: post.published_at,
            edited_at: None,
            content: post.content,
            text: Some(post.text),
            visibility: "public",
            language: post.language,
            sensitive: post.sensitive,
            spoiler_text: post.content_warning.unwrap_or_default(),
            in_reply_to_id: post.reply_to,
            in_reply_to_account_id: None,
            account: Account {
                id: acct.clone(),
                username,
                acct,
                url: post.author.url.clone(),
                uri: post.author.url,
                display_name: post.author.display_name,
                note: String::new(),
                avatar: avatar.clone(),
                avatar_static: avatar,
                header: MISSING_HEADER.to_string(),
                header_static: MISSING_HEADER.to_string(),
                locked: false,
                bot: false,
                group: false,
                discoverable: None,
                indexable: false,
                statuses_count: 0,
                followers_count: 0,
                following_count: 0,
                created_at: post.published_at,
                fields: Vec::new(),
                emojis: Vec::new(),
                last_status_at: None,
            },
            media_attachments,
            mentions: Vec::new(),
            tags: Vec::new(),
            emojis: Vec::new(),
            reblog: None,
            reblogs_count: post.engagement.reposts,
            favourites_count: post.engagement.likes,
            replies_count: post.engagement.replies,
            quotes_count: 0,
            favourited: false,
            reblogged: false,
            muted: false,
            bookmarked: false,
            pinned: false,
            poll: None,
            filtered: Vec::new(),
            card: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use common::types::{Author, Engagement, Media};
    use serde_json::Value;

    use super::*;

    fn sample_post() -> Post {
        Post {
            url: "https://mastodon.social/@alice/123".into(),
            content: "<p>Hello world</p>".into(),
            text: "Hello world".into(),
            author: Author {
                handle: "@alice@mastodon.social".into(),
                display_name: "Alice".into(),
                url: "https://mastodon.social/@alice".into(),
                avatar_url: Some("https://mastodon.social/avatars/alice.png".into()),
            },
            published_at: Utc::now(),
            language: Some("en".into()),
            sensitive: false,
            content_warning: None,
            media: vec![],
            engagement: Engagement {
                replies: 5,
                reposts: 10,
                likes: 42,
            },
            reply_to: None,
            quote_url: None,
        }
    }

    fn sample_post_minimal() -> Post {
        Post {
            url: "https://example.com/post/1".into(),
            content: String::new(),
            text: String::new(),
            author: Author {
                handle: "bob".into(),
                display_name: String::new(),
                url: String::new(),
                avatar_url: None,
            },
            published_at: Utc::now(),
            language: None,
            sensitive: false,
            content_warning: None,
            media: vec![],
            engagement: Engagement::default(),
            reply_to: None,
            quote_url: None,
        }
    }

    // --- Conversion tests ---

    #[test]
    fn basic_fields() {
        let status = Status::from(sample_post());
        assert_eq!(status.id, "https://mastodon.social/@alice/123");
        assert_eq!(status.uri, "https://mastodon.social/@alice/123");
        assert_eq!(
            status.url.as_deref(),
            Some("https://mastodon.social/@alice/123")
        );
        assert_eq!(status.content, "<p>Hello world</p>");
        assert_eq!(status.text.as_deref(), Some("Hello world"));
        assert_eq!(status.visibility, "public");
        assert_eq!(status.language.as_deref(), Some("en"));
        assert!(!status.sensitive);
        assert_eq!(status.spoiler_text, "");
        assert_eq!(status.edited_at, None);
    }

    #[test]
    fn engagement_counts() {
        let status = Status::from(sample_post());
        assert_eq!(status.favourites_count, 42);
        assert_eq!(status.reblogs_count, 10);
        assert_eq!(status.replies_count, 5);
    }

    #[test]
    fn account_fields() {
        let status = Status::from(sample_post());
        let acct = &status.account;
        assert_eq!(acct.username, "alice");
        assert_eq!(acct.acct, "alice@mastodon.social");
        assert_eq!(acct.display_name, "Alice");
        assert_eq!(acct.url, "https://mastodon.social/@alice");
        assert_eq!(acct.uri, "https://mastodon.social/@alice");
        assert_eq!(acct.avatar, "https://mastodon.social/avatars/alice.png");
        assert_eq!(
            acct.avatar_static,
            "https://mastodon.social/avatars/alice.png"
        );
        assert_eq!(acct.note, "");
        assert!(!acct.locked);
        assert!(!acct.bot);
        assert!(!acct.group);
    }

    #[test]
    fn missing_avatar_uses_default() {
        let status = Status::from(sample_post_minimal());
        assert_eq!(status.account.avatar, MISSING_AVATAR);
        assert_eq!(status.account.avatar_static, MISSING_AVATAR);
    }

    #[test]
    fn header_always_has_default() {
        let status = Status::from(sample_post());
        assert_eq!(status.account.header, MISSING_HEADER);
        assert_eq!(status.account.header_static, MISSING_HEADER);
    }

    #[test]
    fn handle_without_at_prefix() {
        let mut post = sample_post();
        post.author.handle = "alice@mastodon.social".into();
        let status = Status::from(post);
        assert_eq!(status.account.username, "alice");
        assert_eq!(status.account.acct, "alice@mastodon.social");
    }

    #[test]
    fn handle_local_user() {
        let mut post = sample_post();
        post.author.handle = "alice".into();
        let status = Status::from(post);
        assert_eq!(status.account.username, "alice");
        assert_eq!(status.account.acct, "alice");
    }

    #[test]
    fn sensitive_with_content_warning() {
        let mut post = sample_post();
        post.sensitive = true;
        post.content_warning = Some("nsfw".into());
        let status = Status::from(post);
        assert!(status.sensitive);
        assert_eq!(status.spoiler_text, "nsfw");
    }

    #[test]
    fn sensitive_without_content_warning() {
        let mut post = sample_post();
        post.sensitive = true;
        let status = Status::from(post);
        assert!(status.sensitive);
        assert_eq!(status.spoiler_text, "");
    }

    #[test]
    fn reply_to_preserved() {
        let mut post = sample_post();
        post.reply_to = Some("https://mastodon.social/@bob/456".into());
        let status = Status::from(post);
        assert_eq!(
            status.in_reply_to_id.as_deref(),
            Some("https://mastodon.social/@bob/456")
        );
        assert_eq!(status.in_reply_to_account_id, None);
    }

    #[test]
    fn media_attachments() {
        let mut post = sample_post();
        post.media = vec![
            Media {
                media_type: "image".into(),
                url: "https://example.com/img.jpg".into(),
                alt: Some("A photo".into()),
                mime_type: Some("image/jpeg".into()),
                width: Some(800),
                height: Some(600),
                blurhash: Some("LEHV6n".into()),
                thumbnail_url: Some("https://example.com/thumb.jpg".into()),
            },
            Media {
                media_type: "video".into(),
                url: "https://example.com/vid.mp4".into(),
                alt: None,
                mime_type: None,
                width: None,
                height: None,
                blurhash: None,
                thumbnail_url: None,
            },
        ];

        let status = Status::from(post);
        assert_eq!(status.media_attachments.len(), 2);

        let img = &status.media_attachments[0];
        assert_eq!(img.media_type, "image");
        assert_eq!(img.url.as_deref(), Some("https://example.com/img.jpg"));
        assert_eq!(img.description.as_deref(), Some("A photo"));
        assert_eq!(img.blurhash.as_deref(), Some("LEHV6n"));
        assert_eq!(
            img.preview_url.as_deref(),
            Some("https://example.com/thumb.jpg")
        );

        let vid = &status.media_attachments[1];
        assert_eq!(vid.media_type, "video");
        assert_eq!(vid.description, None);
        assert_eq!(vid.preview_url, None);
    }

    #[test]
    fn unknown_media_type_normalized() {
        let mut post = sample_post();
        post.media = vec![Media {
            media_type: "document".into(),
            url: "https://example.com/file.pdf".into(),
            alt: None,
            mime_type: None,
            width: None,
            height: None,
            blurhash: None,
            thumbnail_url: None,
        }];

        let status = Status::from(post);
        assert_eq!(status.media_attachments[0].media_type, "unknown");
    }

    #[test]
    fn interaction_flags_default_false() {
        let status = Status::from(sample_post());
        assert!(!status.favourited);
        assert!(!status.reblogged);
        assert!(!status.muted);
        assert!(!status.bookmarked);
        assert!(!status.pinned);
    }

    #[test]
    fn optional_fields_default_to_none_or_empty() {
        let status = Status::from(sample_post());
        assert!(status.reblog.is_none());
        assert!(status.poll.is_none());
        assert!(status.card.is_none());
        assert!(status.mentions.is_empty());
        assert!(status.tags.is_empty());
        assert!(status.emojis.is_empty());
        assert!(status.filtered.is_empty());
        assert!(status.account.fields.is_empty());
        assert!(status.account.emojis.is_empty());
    }

    #[test]
    fn zero_engagement() {
        let status = Status::from(sample_post_minimal());
        assert_eq!(status.favourites_count, 0);
        assert_eq!(status.reblogs_count, 0);
        assert_eq!(status.replies_count, 0);
    }

    #[test]
    fn no_language() {
        let status = Status::from(sample_post_minimal());
        assert_eq!(status.language, None);
    }

    // --- JSON serialization tests ---

    #[test]
    fn json_has_all_required_fields() {
        let status = Status::from(sample_post());
        let json = serde_json::to_value(&status).unwrap();

        let required = [
            "id",
            "uri",
            "url",
            "created_at",
            "content",
            "visibility",
            "sensitive",
            "spoiler_text",
            "account",
            "media_attachments",
            "mentions",
            "tags",
            "emojis",
            "reblogs_count",
            "favourites_count",
            "replies_count",
            "favourited",
            "reblogged",
            "muted",
            "bookmarked",
            "pinned",
        ];

        for field in required {
            assert!(json.get(field).is_some(), "missing required field: {field}");
        }
    }

    #[test]
    fn json_account_has_all_required_fields() {
        let status = Status::from(sample_post());
        let json = serde_json::to_value(&status).unwrap();
        let account = json.get("account").unwrap();

        let required = [
            "id",
            "username",
            "acct",
            "url",
            "uri",
            "display_name",
            "note",
            "avatar",
            "avatar_static",
            "header",
            "header_static",
            "locked",
            "bot",
            "group",
            "statuses_count",
            "followers_count",
            "following_count",
            "created_at",
            "fields",
            "emojis",
        ];

        for field in required {
            assert!(
                account.get(field).is_some(),
                "missing required account field: {field}"
            );
        }
    }

    #[test]
    fn json_account_avatar_header_are_strings() {
        let status = Status::from(sample_post_minimal());
        let json = serde_json::to_value(&status).unwrap();
        let account = json.get("account").unwrap();

        assert!(account["avatar"].is_string());
        assert!(account["avatar_static"].is_string());
        assert!(account["header"].is_string());
        assert!(account["header_static"].is_string());
    }

    #[test]
    fn json_arrays_are_never_null() {
        let status = Status::from(sample_post_minimal());
        let json = serde_json::to_value(&status).unwrap();

        let array_fields = [
            "media_attachments",
            "mentions",
            "tags",
            "emojis",
            "filtered",
        ];
        for field in array_fields {
            assert!(
                json[field].is_array(),
                "{field} must be array, got: {}",
                json[field]
            );
        }

        let account = &json["account"];
        assert!(account["fields"].is_array());
        assert!(account["emojis"].is_array());
    }

    #[test]
    fn json_counts_are_numbers() {
        let status = Status::from(sample_post());
        let json = serde_json::to_value(&status).unwrap();

        assert!(json["reblogs_count"].is_u64());
        assert!(json["favourites_count"].is_u64());
        assert!(json["replies_count"].is_u64());
    }

    #[test]
    fn json_booleans_are_booleans() {
        let status = Status::from(sample_post());
        let json = serde_json::to_value(&status).unwrap();

        let bool_fields = [
            "sensitive",
            "favourited",
            "reblogged",
            "muted",
            "bookmarked",
            "pinned",
        ];
        for field in bool_fields {
            assert!(
                json[field].is_boolean(),
                "{field} must be boolean, got: {}",
                json[field]
            );
        }
    }

    #[test]
    fn json_nullable_fields_present_as_null() {
        let status = Status::from(sample_post());
        let json = serde_json::to_value(&status).unwrap();

        assert!(json.get("in_reply_to_id").is_some());
        assert!(json.get("in_reply_to_account_id").is_some());
        assert!(json.get("reblog").is_some());
        assert!(json.get("poll").is_some());
        assert!(json.get("card").is_some());
        assert!(json.get("edited_at").is_some());
    }

    #[test]
    fn json_media_attachment_type_field_name() {
        let mut post = sample_post();
        post.media = vec![Media {
            media_type: "image".into(),
            url: "https://example.com/img.jpg".into(),
            alt: None,
            mime_type: None,
            width: None,
            height: None,
            blurhash: None,
            thumbnail_url: None,
        }];

        let status = Status::from(post);
        let json = serde_json::to_value(&status).unwrap();
        let attachment = &json["media_attachments"][0];

        assert!(attachment.get("type").is_some());
        assert!(attachment.get("media_type").is_none());
        assert_eq!(attachment["type"], "image");
    }

    #[test]
    fn json_roundtrip_parses_as_valid_object() {
        let status = Status::from(sample_post());
        let json_str = serde_json::to_string(&status).unwrap();
        let parsed: Value = serde_json::from_str(&json_str).unwrap();
        assert!(parsed.is_object());
    }

    #[test]
    fn json_spoiler_text_empty_string_not_null() {
        let status = Status::from(sample_post());
        let json = serde_json::to_value(&status).unwrap();
        assert_eq!(json["spoiler_text"], "");
        assert!(json["spoiler_text"].is_string());
    }

    #[test]
    fn json_display_name_empty_string_not_null() {
        let status = Status::from(sample_post_minimal());
        let json = serde_json::to_value(&status).unwrap();
        assert!(json["account"]["display_name"].is_string());
    }

    #[test]
    fn json_note_empty_string_not_null() {
        let status = Status::from(sample_post());
        let json = serde_json::to_value(&status).unwrap();
        assert_eq!(json["account"]["note"], "");
    }
}
