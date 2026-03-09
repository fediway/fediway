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
        }
    }
}
