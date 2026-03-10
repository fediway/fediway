use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct QueryResponse {
    pub results: Vec<PostResult>,
    pub pagination: Pagination,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Pagination {
    pub cursor: Option<String>,
    pub has_more: bool,
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
    pub avatar_url: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MediaResult {
    #[serde(rename = "type")]
    pub media_type: String,
    pub url: String,
    pub alt: Option<String>,
    pub mime_type: Option<String>,
    pub width: Option<u32>,
    pub height: Option<u32>,
    pub blurhash: Option<String>,
    pub thumbnail_url: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct EngagementResult {
    pub likes: Option<u64>,
    pub reposts: Option<u64>,
    pub replies: Option<u64>,
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

// ---- Tag results (tags/trending) ----

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

// ---- Link results (links/trending) ----

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
    pub image_url: Option<String>,
    pub image_width: Option<i32>,
    pub image_height: Option<i32>,
    pub blurhash: Option<String>,
    pub provider_name: Option<String>,
    pub author_name: Option<String>,
    pub embed_html: Option<String>,
    pub embed_url: Option<String>,
    pub embed_width: Option<i32>,
    pub embed_height: Option<i32>,
    pub language: Option<String>,
    pub published_at: Option<DateTime<Utc>>,
    pub favicon_url: Option<String>,
    pub favicon_blurhash: Option<String>,
    pub post_count: Option<i64>,
    pub account_count: Option<i64>,
    pub score: Option<f64>,
}

#[cfg(test)]
mod tests {
    use super::*;

    // ---- QueryFilters ----

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

    // ---- Tag response deserialization ----

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

    // ---- Link response deserialization ----

    #[test]
    fn deserialize_link_response() {
        let json = serde_json::json!({
            "results": [
                {
                    "url": "https://example.com/article",
                    "title": "Example",
                    "description": "A great article",
                    "type": "link",
                    "imageUrl": "https://cdn.example/og.webp",
                    "imageWidth": 1200,
                    "imageHeight": 630,
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
        assert_eq!(
            link.image_url.as_deref(),
            Some("https://cdn.example/og.webp")
        );
        assert_eq!(link.image_width, Some(1200));
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
                    "type": "link"
                }
            ],
            "pagination": {"cursor": null, "hasMore": false}
        });
        let resp: LinkResponse = serde_json::from_value(json).unwrap();
        let link = &resp.results[0];
        assert_eq!(link.image_url, None);
        assert_eq!(link.blurhash, None);
        assert_eq!(link.provider_name, None);
        assert_eq!(link.post_count, None);
    }
}
