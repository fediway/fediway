use common::types::Link;
use serde::Serialize;

/// Mastodon-compatible `PreviewCard` entity (used for trends/links).
/// See: <https://docs.joinmastodon.org/entities/PreviewCard/>
#[derive(Debug, Serialize)]
pub struct PreviewCard {
    pub url: String,
    pub title: String,
    pub description: String,
    #[serde(rename = "type")]
    pub card_type: String,
    pub author_name: String,
    pub author_url: String,
    pub provider_name: String,
    pub provider_url: String,
    pub html: String,
    pub width: i32,
    pub height: i32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub image: Option<String>,
    pub image_description: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub embed_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub blurhash: Option<String>,
}

impl From<Link> for PreviewCard {
    fn from(link: Link) -> Self {
        Self {
            url: link.url,
            title: link.title,
            description: link.description,
            card_type: link.link_type,
            author_name: link.author_name.unwrap_or_default(),
            author_url: String::new(),
            provider_name: link.provider_name.unwrap_or_default(),
            provider_url: String::new(),
            html: String::new(),
            width: link.image_width.unwrap_or(0),
            height: link.image_height.unwrap_or(0),
            image: link.image_url,
            image_description: String::new(),
            embed_url: link.embed_url,
            blurhash: link.blurhash,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_card() -> PreviewCard {
        PreviewCard {
            url: "https://example.com/article".into(),
            title: "Example Article".into(),
            description: "A great article".into(),
            card_type: "link".into(),
            author_name: "Alice".into(),
            author_url: String::new(),
            provider_name: "Example News".into(),
            provider_url: String::new(),
            html: String::new(),
            width: 1200,
            height: 630,
            image: Some("https://cdn.example/og.webp".into()),
            image_description: String::new(),
            embed_url: None,
            blurhash: Some("LEHV6nWB2yk8".into()),
        }
    }

    #[test]
    fn type_field_renamed() {
        let json = serde_json::to_value(sample_card()).unwrap();
        assert_eq!(json["type"], "link");
        assert!(json.get("card_type").is_none());
    }

    #[test]
    fn required_fields_present() {
        let json = serde_json::to_value(sample_card()).unwrap();
        for field in [
            "url",
            "title",
            "description",
            "type",
            "author_name",
            "author_url",
            "provider_name",
            "provider_url",
            "html",
            "width",
            "height",
            "image_description",
        ] {
            assert!(json.get(field).is_some(), "missing field: {field}");
        }
    }

    #[test]
    fn optional_fields_omitted_when_none() {
        let card = PreviewCard {
            image: None,
            embed_url: None,
            blurhash: None,
            ..sample_card()
        };
        let json = serde_json::to_value(&card).unwrap();
        assert!(json.get("image").is_none());
        assert!(json.get("embed_url").is_none());
        assert!(json.get("blurhash").is_none());
    }

    #[test]
    fn dimensions_are_numbers() {
        let json = serde_json::to_value(sample_card()).unwrap();
        assert_eq!(json["width"], 1200);
        assert_eq!(json["height"], 630);
    }

    #[test]
    fn empty_strings_not_null() {
        let json = serde_json::to_value(sample_card()).unwrap();
        assert_eq!(json["author_url"], "");
        assert_eq!(json["provider_url"], "");
        assert_eq!(json["html"], "");
        assert_eq!(json["image_description"], "");
    }
}
