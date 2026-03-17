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
    pub meta: Option<MediaMeta>,
    pub description: Option<String>,
    pub blurhash: Option<String>,
}

/// Mastodon-compatible media metadata.
#[derive(Debug, Serialize)]
pub struct MediaMeta {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub original: Option<MediaMetaDimensions>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub small: Option<MediaMetaDimensions>,
}

/// Width/height/aspect for a media variant.
#[derive(Debug, Serialize)]
pub struct MediaMetaDimensions {
    pub width: u32,
    pub height: u32,
    pub aspect: f64,
}

impl MediaMetaDimensions {
    pub fn new(width: u32, height: u32) -> Self {
        let aspect = if height > 0 {
            f64::from(width) / f64::from(height)
        } else {
            1.0
        };
        Self {
            width,
            height,
            aspect,
        }
    }
}

pub fn normalize_media_type(t: &str) -> String {
    match t {
        "image" | "video" | "gifv" | "audio" => t.to_string(),
        _ => "unknown".to_string(),
    }
}
