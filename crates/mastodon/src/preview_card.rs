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
    pub authors: Vec<PreviewCardAuthor>,
    pub author_name: String,
    pub author_url: String,
    pub provider_name: String,
    pub provider_url: String,
    pub html: String,
    pub width: i32,
    pub height: i32,
    pub image: Option<String>,
    pub image_description: String,
    pub embed_url: Option<String>,
    pub blurhash: Option<String>,
    pub history: Vec<PreviewCardHistory>,
}

/// Author of a preview card (added in Mastodon 4.3).
#[derive(Debug, Serialize)]
pub struct PreviewCardAuthor {
    pub name: String,
    pub url: String,
    pub account: Option<()>,
}

/// Daily usage history for trending links.
#[derive(Debug, Serialize)]
pub struct PreviewCardHistory {
    pub day: String,
    pub accounts: String,
    pub uses: String,
}

impl From<Link> for PreviewCard {
    fn from(link: Link) -> Self {
        let authors = link
            .author_name
            .as_ref()
            .filter(|n| !n.is_empty())
            .map(|name| {
                vec![PreviewCardAuthor {
                    name: name.clone(),
                    url: String::new(),
                    account: None,
                }]
            })
            .unwrap_or_default();

        Self {
            url: link.url,
            title: link.title,
            description: link.description,
            card_type: link.link_type,
            authors,
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
            history: Vec::new(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_link() -> Link {
        Link {
            url: "https://example.com/article".into(),
            title: "Example Article".into(),
            description: "A great article".into(),
            link_type: "link".into(),
            author_name: Some("Alice".into()),
            provider_name: Some("Example News".into()),
            image_url: Some("https://cdn.example/og.webp".into()),
            image_width: Some(1200),
            image_height: Some(630),
            blurhash: Some("LEHV6nWB2yk8".into()),
            embed_url: None,
        }
    }

    #[test]
    fn from_domain_link_maps_all_fields() {
        let card = PreviewCard::from(sample_link());
        assert_eq!(card.url, "https://example.com/article");
        assert_eq!(card.title, "Example Article");
        assert_eq!(card.description, "A great article");
        assert_eq!(card.card_type, "link");
        assert_eq!(card.author_name, "Alice");
        assert_eq!(card.provider_name, "Example News");
        assert_eq!(card.width, 1200);
        assert_eq!(card.height, 630);
        assert_eq!(card.image.as_deref(), Some("https://cdn.example/og.webp"));
        assert_eq!(card.blurhash.as_deref(), Some("LEHV6nWB2yk8"));
    }

    #[test]
    fn from_domain_link_defaults_optional_fields() {
        let link = Link {
            author_name: None,
            provider_name: None,
            image_url: None,
            image_width: None,
            image_height: None,
            blurhash: None,
            embed_url: None,
            ..sample_link()
        };
        let card = PreviewCard::from(link);
        assert_eq!(card.author_name, "");
        assert_eq!(card.provider_name, "");
        assert_eq!(card.width, 0);
        assert_eq!(card.height, 0);
        assert!(card.image.is_none());
        assert!(card.blurhash.is_none());
    }

    #[test]
    fn from_domain_link_sets_empty_strings() {
        let card = PreviewCard::from(sample_link());
        assert_eq!(card.author_url, "");
        assert_eq!(card.provider_url, "");
        assert_eq!(card.html, "");
        assert_eq!(card.image_description, "");
    }

    fn sample_card() -> PreviewCard {
        PreviewCard {
            url: "https://example.com/article".into(),
            title: "Example Article".into(),
            description: "A great article".into(),
            card_type: "link".into(),
            authors: vec![PreviewCardAuthor {
                name: "Alice".into(),
                url: String::new(),
                account: None,
            }],
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
            history: Vec::new(),
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
            "authors",
            "history",
        ] {
            assert!(json.get(field).is_some(), "missing field: {field}");
        }
    }

    #[test]
    fn nullable_fields_present_as_null() {
        let card = PreviewCard {
            image: None,
            embed_url: None,
            blurhash: None,
            ..sample_card()
        };
        let json = serde_json::to_value(&card).unwrap();
        assert!(json.get("image").is_some(), "image must be present as null");
        assert!(json["image"].is_null());
        assert!(
            json.get("embed_url").is_some(),
            "embed_url must be present as null"
        );
        assert!(json["embed_url"].is_null());
        assert!(
            json.get("blurhash").is_some(),
            "blurhash must be present as null"
        );
        assert!(json["blurhash"].is_null());
    }

    #[test]
    fn authors_populated_from_author_name() {
        let card = PreviewCard::from(sample_link());
        assert_eq!(card.authors.len(), 1);
        assert_eq!(card.authors[0].name, "Alice");
    }

    #[test]
    fn authors_empty_when_no_author() {
        let link = Link {
            author_name: None,
            ..sample_link()
        };
        let card = PreviewCard::from(link);
        assert!(card.authors.is_empty());
    }

    #[test]
    fn history_empty_by_default() {
        let card = PreviewCard::from(sample_link());
        assert!(card.history.is_empty());
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
