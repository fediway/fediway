use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Post {
    pub url: String,
    pub content: String,
    pub text: String,
    pub author: Author,
    pub published_at: DateTime<Utc>,
    pub language: Option<String>,
    pub sensitive: bool,
    pub content_warning: Option<String>,
    pub media: Vec<Media>,
    pub engagement: Engagement,
    pub reply_to: Option<String>,
    pub quote_url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Author {
    pub handle: String,
    pub display_name: String,
    pub url: String,
    pub avatar_url: Option<String>,
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

pub struct Provider {
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
