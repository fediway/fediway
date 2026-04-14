use chrono::{DateTime, Utc};
use serde::Serialize;

/// Mastodon-compatible Account entity.
/// See: <https://docs.joinmastodon.org/entities/Account/>
#[derive(Debug, Clone, Serialize)]
#[allow(clippy::struct_excessive_bools)]
pub struct Account {
    pub id: String,
    pub username: String,
    pub acct: String,
    pub url: String,
    pub uri: String,
    pub display_name: String,
    pub note: String,
    pub avatar: String,
    pub avatar_static: String,
    pub header: String,
    pub header_static: String,
    pub locked: bool,
    pub bot: bool,
    pub group: bool,
    pub discoverable: Option<bool>,
    pub indexable: bool,
    pub statuses_count: u64,
    pub followers_count: u64,
    pub following_count: u64,
    pub created_at: DateTime<Utc>,
    pub fields: Vec<Field>,
    pub emojis: Vec<CustomEmoji>,
    pub last_status_at: Option<String>,
}

/// Mastodon-compatible `CustomEmoji` entity.
#[derive(Debug, Clone, Serialize)]
pub struct CustomEmoji {
    pub shortcode: String,
    pub url: String,
    pub static_url: String,
    pub visible_in_picker: bool,
}

/// Mastodon-compatible Field entity (profile metadata).
#[derive(Debug, Clone, Serialize)]
pub struct Field {
    pub name: String,
    pub value: String,
    pub verified_at: Option<DateTime<Utc>>,
}
