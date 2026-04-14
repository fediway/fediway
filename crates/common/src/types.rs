use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Post {
    #[serde(default)]
    pub provider_id: Option<i64>,
    #[serde(default)]
    pub provider_domain: Option<String>,
    pub url: String,
    #[serde(default)]
    pub uri: Option<String>,
    pub content: String,
    pub text: String,
    pub author: Author,
    pub published_at: DateTime<Utc>,
    pub language: Option<String>,
    pub sensitive: bool,
    pub content_warning: Option<String>,
    pub media: Vec<Media>,
    pub engagement: Engagement,
    pub link: Option<CardPreview>,
    pub reply_to: Option<Box<Post>>,
    pub quote: Option<Box<Post>>,
    pub tags: Vec<String>,
    pub emojis: Vec<CustomEmoji>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomEmoji {
    pub shortcode: String,
    pub url: String,
    pub static_url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CardPreview {
    pub url: String,
    pub title: String,
    pub description: String,
    pub link_type: String,
    pub author_name: Option<String>,
    pub provider_name: Option<String>,
    pub image_url: Option<String>,
    pub image_width: Option<i32>,
    pub image_height: Option<i32>,
    pub blurhash: Option<String>,
    pub embed_url: Option<String>,
    pub embed_html: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Author {
    pub handle: String,
    pub display_name: String,
    pub url: String,
    pub avatar_url: Option<String>,
    pub header_url: Option<String>,
    pub emojis: Vec<CustomEmoji>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Media {
    pub media_type: String,
    pub url: String,
    pub alt: Option<String>,
    pub mime_type: Option<String>,
    pub width: Option<u32>,
    pub height: Option<u32>,
    pub blurhash: Option<String>,
    pub thumbnail_url: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Engagement {
    pub replies: u64,
    pub reposts: u64,
    pub likes: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Follow {
    pub follower_id: String,
    pub followed_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Interaction {
    pub actor_id: String,
    pub post_id: String,
    pub kind: InteractionKind,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum InteractionKind {
    Like,
    Repost,
    Reply,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tag {
    pub name: String,
    pub url: String,
    pub history: Vec<TagHistory>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TagHistory {
    pub day: String,
    pub uses: i64,
    pub accounts: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Link {
    pub url: String,
    pub title: String,
    pub description: String,
    pub link_type: String,
    pub author_name: Option<String>,
    pub provider_name: Option<String>,
    pub image_url: Option<String>,
    pub image_width: Option<i32>,
    pub image_height: Option<i32>,
    pub blurhash: Option<String>,
    pub embed_url: Option<String>,
    pub embed_html: Option<String>,
    pub post_count: i64,
    pub account_count: i64,
}

pub struct Provider {
    pub domain: String,
    pub base_url: String,
    pub api_key: String,
    pub max_results: usize,
    pub supported_filters: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ProviderStatus {
    Pending,
    Approved,
    Failed,
}

impl ProviderStatus {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Approved => "approved",
            Self::Failed => "failed",
        }
    }
}
