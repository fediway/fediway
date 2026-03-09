use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Post {
    pub id: String,
    pub author: Author,
    pub text: String,
    pub language: Option<String>,
    pub published_at: DateTime<Utc>,
    pub engagement: Engagement,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Author {
    pub id: String,
    pub username: String,
    pub display_name: Option<String>,
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
