use serde::Serialize;

/// Mastodon-compatible Mention entity.
#[derive(Debug, Serialize)]
pub struct Mention {
    pub id: String,
    pub username: String,
    pub url: String,
    pub acct: String,
}
