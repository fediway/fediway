use serde::Serialize;

/// Mastodon-compatible Tag entity.
#[derive(Debug, Serialize)]
pub struct Tag {
    pub name: String,
    pub url: String,
}
