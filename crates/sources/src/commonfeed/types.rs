use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Pagination {
    pub cursor: Option<String>,
    pub has_more: bool,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct QueryResponse {
    pub results: Vec<PostResult>,
    pub pagination: Pagination,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PostResult {
    pub url: String,
    pub protocol: String,
    #[serde(rename = "type")]
    pub content_type: String,
    pub content: String,
    pub text: String,
    pub author: AuthorResult,
    pub timestamp: DateTime<Utc>,
    pub language: Option<String>,
    pub sensitive: Option<bool>,
    pub content_warning: Option<String>,
    pub media: Option<Vec<MediaResult>>,
    pub engagement: Option<EngagementResult>,
    pub reply_to: Option<String>,
    pub quote_url: Option<String>,
    pub score: Option<f64>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AuthorResult {
    pub name: String,
    pub handle: String,
    pub url: String,
    pub avatar: Option<ImageObject>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MediaResult {
    #[serde(rename = "type")]
    pub media_type: String,
    pub alt: Option<String>,
    pub image: Option<ImageObject>,
    pub original: Option<MediaOriginal>,
    pub sizes: Option<Sizes>,
    pub poster: Option<ImageObject>,
}

#[derive(Debug, Deserialize)]
pub struct EngagementResult {
    pub likes: Option<i32>,
    pub reposts: Option<i32>,
    pub replies: Option<i32>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ImageObject {
    pub sizes: Sizes,
    pub blurhash: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Sizes {
    pub small: Option<SizeVariant>,
    pub medium: Option<SizeVariant>,
    pub large: SizeVariant,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SizeVariant {
    pub url: String,
    pub width: Option<i32>,
    pub height: Option<i32>,
    pub mime_type: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MediaOriginal {
    pub width: i32,
    pub height: i32,
}

#[derive(Debug, Default, Clone, Serialize)]
pub struct QueryFilters {
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub language: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tag: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub link: Option<String>,
}

impl QueryFilters {
    #[must_use]
    pub fn for_provider(&self, supported: &[String]) -> Self {
        Self {
            language: if supported.iter().any(|s| s == "language") {
                self.language.clone()
            } else {
                Vec::new()
            },
            tag: if supported.iter().any(|s| s == "tag") {
                self.tag.clone()
            } else {
                None
            },
            link: if supported.iter().any(|s| s == "link") {
                self.link.clone()
            } else {
                None
            },
        }
    }
}

#[derive(Debug, Deserialize)]
pub struct TagResponse {
    pub results: Vec<TagResult>,
    pub pagination: Pagination,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TagResult {
    pub name: String,
    pub post_count: i64,
    pub account_count: i64,
    #[serde(default)]
    pub history: Option<Vec<TagHistoryItem>>,
    pub score: Option<f64>,
}

#[derive(Debug, Deserialize)]
pub struct TagHistoryItem {
    pub day: String,
    pub uses: i64,
    pub accounts: i64,
}

#[derive(Debug, Deserialize)]
pub struct LinkResponse {
    pub results: Vec<LinkResult>,
    pub pagination: Pagination,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LinkResult {
    pub url: String,
    pub title: String,
    pub description: String,
    #[serde(rename = "type")]
    pub link_type: String,
    pub image: Option<ImageObject>,
    pub provider_name: Option<String>,
    pub author_name: Option<String>,
    pub embed_html: Option<String>,
    pub embed_url: Option<String>,
    pub language: Option<String>,
    pub published_at: Option<DateTime<Utc>>,
    pub favicon: Option<ImageObject>,
    pub post_count: i64,
    pub account_count: i64,
    pub score: Option<f64>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tag_filter_serializes() {
        let filters = QueryFilters {
            tag: Some("rust".into()),
            ..Default::default()
        };
        let json = serde_json::to_value(&filters).unwrap();
        assert_eq!(json, serde_json::json!({"tag": "rust"}));
    }

    #[test]
    fn link_filter_serializes() {
        let filters = QueryFilters {
            link: Some("https://example.com".into()),
            ..Default::default()
        };
        let json = serde_json::to_value(&filters).unwrap();
        assert_eq!(json, serde_json::json!({"link": "https://example.com"}));
    }

    #[test]
    fn for_provider_includes_tag_when_supported() {
        let filters = QueryFilters {
            tag: Some("rust".into()),
            ..Default::default()
        };
        let supported = vec!["tag".to_string()];
        let result = filters.for_provider(&supported);
        assert_eq!(result.tag.as_deref(), Some("rust"));
    }

    #[test]
    fn for_provider_excludes_tag_when_unsupported() {
        let filters = QueryFilters {
            tag: Some("rust".into()),
            ..Default::default()
        };
        let supported = vec!["language".to_string()];
        let result = filters.for_provider(&supported);
        assert_eq!(result.tag, None);
    }

    #[test]
    fn for_provider_includes_link_when_supported() {
        let filters = QueryFilters {
            link: Some("https://example.com".into()),
            ..Default::default()
        };
        let supported = vec!["link".to_string()];
        let result = filters.for_provider(&supported);
        assert_eq!(result.link.as_deref(), Some("https://example.com"));
    }

    #[test]
    fn for_provider_excludes_link_when_unsupported() {
        let filters = QueryFilters {
            link: Some("https://example.com".into()),
            ..Default::default()
        };
        let supported = vec!["language".to_string()];
        let result = filters.for_provider(&supported);
        assert_eq!(result.link, None);
    }

    #[test]
    fn language_filter_serializes() {
        let filters = QueryFilters {
            language: vec!["en".into(), "de".into()],
            ..Default::default()
        };
        let json = serde_json::to_value(&filters).unwrap();
        assert_eq!(json, serde_json::json!({"language": ["en", "de"]}));
    }

    #[test]
    fn empty_filters_serialize_empty() {
        let filters = QueryFilters::default();
        let json = serde_json::to_value(&filters).unwrap();
        assert_eq!(json, serde_json::json!({}));
    }

    #[test]
    fn for_provider_includes_language_when_supported() {
        let filters = QueryFilters {
            language: vec!["en".into()],
            ..Default::default()
        };
        let supported = vec!["language".to_string(), "protocol".to_string()];
        let result = filters.for_provider(&supported);
        assert_eq!(result.language, vec!["en"]);
    }

    #[test]
    fn for_provider_excludes_language_when_unsupported() {
        let filters = QueryFilters {
            language: vec!["en".into()],
            ..Default::default()
        };
        let supported = vec!["protocol".to_string()];
        let result = filters.for_provider(&supported);
        assert!(result.language.is_empty());
    }

    #[test]
    fn deserialize_post_response() {
        let json = serde_json::json!({
            "requestId": "req-abc",
            "algorithm": "trending",
            "results": [
                {
                    "url": "https://mastodon.social/@alice/123",
                    "protocol": "activitypub",
                    "identifiers": {"activitypub": "https://mastodon.social/users/alice/statuses/123"},
                    "type": "post",
                    "content": "<p>hello world</p>",
                    "text": "hello world",
                    "author": {
                        "name": "Alice",
                        "handle": "@alice@mastodon.social",
                        "url": "https://mastodon.social/@alice",
                        "identifiers": {"activitypub": "https://mastodon.social/users/alice"},
                        "avatar": {
                            "sizes": {
                                "large": {
                                    "url": "https://cdn.mastodon.social/avatars/alice.webp",
                                    "mimeType": "image/webp"
                                }
                            }
                        }
                    },
                    "timestamp": "2026-03-16T12:00:00Z",
                    "language": "en",
                    "engagement": {"likes": 42, "reposts": 10, "replies": 5},
                    "media": [
                        {
                            "type": "image",
                            "alt": "A sunset",
                            "image": {
                                "sizes": {
                                    "small": {
                                        "url": "https://cdn.example/small/sunset.webp",
                                        "width": 400,
                                        "height": 300
                                    },
                                    "large": {
                                        "url": "https://cdn.example/sunset.webp",
                                        "width": 1920,
                                        "height": 1080,
                                        "mimeType": "image/webp"
                                    }
                                },
                                "blurhash": "LEHV6nWB2yk8"
                            },
                            "original": {"width": 3840, "height": 2160}
                        }
                    ],
                    "score": 0.95
                }
            ],
            "pagination": {
                "cursor": "abc123",
                "cursorExpiresAt": "2026-03-17T00:00:00Z",
                "hasMore": true
            }
        });

        let resp: QueryResponse = serde_json::from_value(json).unwrap();
        assert_eq!(resp.results.len(), 1);

        let post = &resp.results[0];
        assert_eq!(post.url, "https://mastodon.social/@alice/123");
        assert_eq!(post.content_type, "post");
        assert_eq!(post.author.name, "Alice");

        let avatar = post.author.avatar.as_ref().unwrap();
        assert_eq!(
            avatar.sizes.large.url,
            "https://cdn.mastodon.social/avatars/alice.webp"
        );

        let media = post.media.as_ref().unwrap();
        assert_eq!(media[0].media_type, "image");
        let img = media[0].image.as_ref().unwrap();
        assert_eq!(img.sizes.large.width, Some(1920));
        assert_eq!(img.blurhash.as_deref(), Some("LEHV6nWB2yk8"));
        assert_eq!(
            img.sizes.small.as_ref().unwrap().url,
            "https://cdn.example/small/sunset.webp"
        );

        let original = media[0].original.as_ref().unwrap();
        assert_eq!(original.width, 3840);

        let engagement = post.engagement.as_ref().unwrap();
        assert_eq!(engagement.likes, Some(42));

        assert_eq!(resp.pagination.cursor.as_deref(), Some("abc123"));
        assert!(resp.pagination.has_more);
    }

    #[test]
    fn deserialize_post_with_video_media() {
        let json = serde_json::json!({
            "results": [{
                "url": "https://example.com/post/1",
                "protocol": "activitypub",
                "identifiers": {},
                "type": "post",
                "content": "<p>check this</p>",
                "text": "check this",
                "author": {
                    "name": "Bob",
                    "handle": "@bob@example.com",
                    "url": "https://example.com/@bob",
                    "identifiers": {}
                },
                "timestamp": "2026-03-16T12:00:00Z",
                "media": [{
                    "type": "video",
                    "alt": "A clip",
                    "sizes": {
                        "large": {
                            "url": "https://cdn.example/video.mp4",
                            "mimeType": "video/mp4"
                        }
                    },
                    "poster": {
                        "sizes": {
                            "large": {
                                "url": "https://cdn.example/poster.webp",
                                "width": 1280,
                                "height": 720
                            }
                        },
                        "blurhash": "L6PZfSi_.AyE"
                    },
                    "original": {"width": 1920, "height": 1080}
                }]
            }],
            "pagination": {"hasMore": false}
        });

        let resp: QueryResponse = serde_json::from_value(json).unwrap();
        let media = &resp.results[0].media.as_ref().unwrap()[0];
        assert_eq!(media.media_type, "video");
        assert!(media.image.is_none());

        let sizes = media.sizes.as_ref().unwrap();
        assert_eq!(sizes.large.url, "https://cdn.example/video.mp4");
        assert_eq!(sizes.large.mime_type.as_deref(), Some("video/mp4"));

        let poster = media.poster.as_ref().unwrap();
        assert_eq!(poster.sizes.large.url, "https://cdn.example/poster.webp");
        assert_eq!(poster.blurhash.as_deref(), Some("L6PZfSi_.AyE"));
    }

    #[test]
    fn deserialize_post_minimal() {
        let json = serde_json::json!({
            "results": [{
                "url": "https://example.com/post/1",
                "protocol": "activitypub",
                "identifiers": {},
                "type": "post",
                "content": "",
                "text": "",
                "author": {
                    "name": "A",
                    "handle": "@a@example.com",
                    "url": "https://example.com/@a",
                    "identifiers": {}
                },
                "timestamp": "2026-03-16T00:00:00Z"
            }],
            "pagination": {"hasMore": false}
        });

        let resp: QueryResponse = serde_json::from_value(json).unwrap();
        let post = &resp.results[0];
        assert!(post.author.avatar.is_none());
        assert!(post.media.is_none());
        assert!(post.engagement.is_none());
        assert!(post.score.is_none());
    }

    #[test]
    fn deserialize_tag_response() {
        let json = serde_json::json!({
            "results": [
                {
                    "name": "rust",
                    "postCount": 42,
                    "accountCount": 15,
                    "history": [{"day": "1709251200", "uses": 30, "accounts": 12}],
                    "score": 0.95
                }
            ],
            "pagination": {"cursor": null, "hasMore": false}
        });
        let resp: TagResponse = serde_json::from_value(json).unwrap();
        assert_eq!(resp.results.len(), 1);
        assert_eq!(resp.results[0].name, "rust");
        assert_eq!(resp.results[0].post_count, 42);
        assert_eq!(resp.results[0].account_count, 15);
        let history = resp.results[0].history.as_ref().unwrap();
        assert_eq!(history[0].uses, 30);
        assert_eq!(history[0].accounts, 12);
    }

    #[test]
    fn deserialize_tag_without_history() {
        let json = serde_json::json!({
            "results": [{"name": "fediverse", "postCount": 5, "accountCount": 3}],
            "pagination": {"cursor": null, "hasMore": false}
        });
        let resp: TagResponse = serde_json::from_value(json).unwrap();
        assert!(resp.results[0].history.is_none());
        assert_eq!(resp.results[0].score, None);
    }

    #[test]
    fn deserialize_link_response() {
        let json = serde_json::json!({
            "results": [
                {
                    "url": "https://example.com/article",
                    "title": "Example",
                    "description": "A great article",
                    "type": "link",
                    "image": {
                        "sizes": {
                            "large": {
                                "url": "https://cdn.example/og.webp",
                                "width": 1200,
                                "height": 630,
                                "mimeType": "image/webp"
                            }
                        },
                        "blurhash": "LEHV6nWB2yk8"
                    },
                    "providerName": "Example News",
                    "postCount": 42,
                    "accountCount": 15,
                    "score": 0.8
                }
            ],
            "pagination": {"cursor": null, "hasMore": false}
        });
        let resp: LinkResponse = serde_json::from_value(json).unwrap();
        assert_eq!(resp.results.len(), 1);
        let link = &resp.results[0];
        assert_eq!(link.url, "https://example.com/article");
        assert_eq!(link.title, "Example");
        assert_eq!(link.link_type, "link");
        let img = link.image.as_ref().unwrap();
        assert_eq!(img.sizes.large.url, "https://cdn.example/og.webp");
        assert_eq!(img.sizes.large.width, Some(1200));
        assert_eq!(img.blurhash.as_deref(), Some("LEHV6nWB2yk8"));
        assert_eq!(link.provider_name.as_deref(), Some("Example News"));
    }

    #[test]
    fn deserialize_link_minimal() {
        let json = serde_json::json!({
            "results": [
                {
                    "url": "https://example.com",
                    "title": "Example",
                    "description": "",
                    "type": "link",
                    "postCount": 0,
                    "accountCount": 0
                }
            ],
            "pagination": {"cursor": null, "hasMore": false}
        });
        let resp: LinkResponse = serde_json::from_value(json).unwrap();
        let link = &resp.results[0];
        assert!(link.image.is_none());
        assert_eq!(link.provider_name, None);
        assert_eq!(link.post_count, 0);
    }
}
