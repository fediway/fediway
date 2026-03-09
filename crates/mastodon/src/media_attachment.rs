use serde::Serialize;

/// Mastodon-compatible `MediaAttachment` entity.
/// See: <https://docs.joinmastodon.org/entities/MediaAttachment/>
#[derive(Debug, Serialize)]
pub struct MediaAttachment {
    pub id: String,
    #[serde(rename = "type")]
    pub media_type: String,
    pub url: Option<String>,
    pub preview_url: Option<String>,
    pub remote_url: Option<String>,
    pub meta: Option<()>,
    pub description: Option<String>,
    pub blurhash: Option<String>,
}

pub fn normalize_media_type(t: &str) -> String {
    match t {
        "image" | "video" | "gifv" | "audio" => t.to_string(),
        _ => "unknown".to_string(),
    }
}
