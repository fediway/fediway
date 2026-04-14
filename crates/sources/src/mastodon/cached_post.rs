use common::types::Post;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum CachedPost {
    Local { id: i64 },
    Remote { post: Box<Post> },
}

impl CachedPost {
    #[must_use]
    pub fn from_post(post: Post, instance_domain: &str) -> Self {
        match (&post.provider_domain, post.provider_id) {
            (Some(domain), Some(id)) if domain == instance_domain => Self::Local { id },
            _ => Self::Remote {
                post: Box::new(post),
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use common::types::{Author, Engagement, Post};

    use super::*;

    fn post(provider_domain: Option<&str>, provider_id: Option<i64>) -> Post {
        Post {
            provider_id,
            provider_domain: provider_domain.map(str::to_owned),
            url: "https://example/p/1".into(),
            uri: None,
            content: String::new(),
            text: String::new(),
            author: Author {
                handle: "alice".into(),
                display_name: String::new(),
                url: String::new(),
                avatar_url: None,
                header_url: None,
                emojis: Vec::new(),
            },
            published_at: chrono::Utc::now(),
            language: None,
            sensitive: false,
            content_warning: None,
            media: Vec::new(),
            engagement: Engagement::default(),
            link: None,
            reply_to: None,
            quote: None,
            tags: Vec::new(),
            emojis: Vec::new(),
        }
    }

    #[test]
    fn local_when_provider_domain_matches_and_id_present() {
        let p = post(Some("local.test"), Some(42));
        match CachedPost::from_post(p, "local.test") {
            CachedPost::Local { id } => assert_eq!(id, 42),
            CachedPost::Remote { .. } => panic!("expected Local"),
        }
    }

    #[test]
    fn remote_when_provider_domain_differs() {
        let p = post(Some("other.example"), Some(42));
        assert!(matches!(
            CachedPost::from_post(p, "local.test"),
            CachedPost::Remote { .. }
        ));
    }

    #[test]
    fn remote_when_provider_id_missing() {
        let p = post(Some("local.test"), None);
        assert!(matches!(
            CachedPost::from_post(p, "local.test"),
            CachedPost::Remote { .. }
        ));
    }

    #[test]
    fn remote_when_provider_domain_missing() {
        let p = post(None, Some(42));
        assert!(matches!(
            CachedPost::from_post(p, "local.test"),
            CachedPost::Remote { .. }
        ));
    }
}
