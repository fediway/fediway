use common::types;
use serde::Serialize;

/// Mastodon-compatible Tag entity.
/// See: <https://docs.joinmastodon.org/entities/Tag/>
#[derive(Debug, Clone, Serialize)]
pub struct Tag {
    pub name: String,
    pub url: String,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub history: Vec<TagHistory>,
}

/// Daily usage history for a tag.
/// Mastodon returns `uses` and `accounts` as strings.
#[derive(Debug, Clone, Serialize)]
pub struct TagHistory {
    pub day: String,
    pub uses: String,
    pub accounts: String,
}

impl From<types::Tag> for Tag {
    fn from(tag: types::Tag) -> Self {
        let history = tag
            .history
            .into_iter()
            .map(|h| TagHistory {
                day: h.day,
                uses: h.uses.to_string(),
                accounts: h.accounts.to_string(),
            })
            .collect();

        Self {
            name: tag.name,
            url: tag.url,
            history,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn from_domain_tag_with_history() {
        let domain_tag = types::Tag {
            name: "rust".into(),
            url: "/tags/rust".into(),
            history: vec![types::TagHistory {
                day: "1709251200".into(),
                uses: 30,
                accounts: 12,
            }],
        };
        let tag = Tag::from(domain_tag);
        assert_eq!(tag.name, "rust");
        assert_eq!(tag.url, "/tags/rust");
        assert_eq!(tag.history.len(), 1);
        assert_eq!(tag.history[0].uses, "30");
        assert_eq!(tag.history[0].accounts, "12");
    }

    #[test]
    fn from_domain_tag_without_history() {
        let domain_tag = types::Tag {
            name: "fediverse".into(),
            url: "/tags/fediverse".into(),
            history: Vec::new(),
        };
        let tag = Tag::from(domain_tag);
        assert_eq!(tag.name, "fediverse");
        assert!(tag.history.is_empty());
    }

    #[test]
    fn from_domain_tag_converts_integers_to_strings() {
        let domain_tag = types::Tag {
            name: "test".into(),
            url: "/tags/test".into(),
            history: vec![types::TagHistory {
                day: "1709251200".into(),
                uses: 0,
                accounts: 0,
            }],
        };
        let tag = Tag::from(domain_tag);
        assert_eq!(tag.history[0].uses, "0");
        assert_eq!(tag.history[0].accounts, "0");
    }

    #[test]
    fn tag_serializes_with_history() {
        let tag = Tag {
            name: "rust".into(),
            url: "/tags/rust".into(),
            history: vec![TagHistory {
                day: "1709251200".into(),
                uses: "30".into(),
                accounts: "12".into(),
            }],
        };
        let json = serde_json::to_value(&tag).unwrap();
        assert_eq!(json["name"], "rust");
        assert_eq!(json["url"], "/tags/rust");
        let h = &json["history"][0];
        assert_eq!(h["day"], "1709251200");
        assert_eq!(h["uses"], "30");
        assert!(h["uses"].is_string(), "uses must be a string");
        assert_eq!(h["accounts"], "12");
        assert!(h["accounts"].is_string(), "accounts must be a string");
    }

    #[test]
    fn tag_without_history_omits_field() {
        let tag = Tag {
            name: "fediverse".into(),
            url: "/tags/fediverse".into(),
            history: Vec::new(),
        };
        let json = serde_json::to_value(&tag).unwrap();
        assert!(json.get("history").is_none());
    }

    #[test]
    fn tag_json_has_required_fields() {
        let tag = Tag {
            name: "test".into(),
            url: "/tags/test".into(),
            history: Vec::new(),
        };
        let json = serde_json::to_value(&tag).unwrap();
        assert!(json.get("name").is_some());
        assert!(json.get("url").is_some());
    }
}
