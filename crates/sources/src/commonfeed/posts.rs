use std::future::Future;
use std::pin::Pin;

use common::types::{Author, Engagement, Media, Post, Provider};
use pipeline::candidate::Candidate;
use pipeline::source::Source;

use super::types::{PostResult, QueryFilters, QueryResponse};

pub struct PostsSource {
    algorithm: String,
    provider: Provider,
    filters: QueryFilters,
}

impl PostsSource {
    #[must_use]
    pub fn new(provider: Provider, algorithm: impl Into<String>) -> Self {
        Self {
            algorithm: algorithm.into(),
            provider,
            filters: QueryFilters::default(),
        }
    }

    #[must_use]
    pub fn with_filters(mut self, filters: QueryFilters) -> Self {
        self.filters = filters;
        self
    }
}

impl Source<Post> for PostsSource {
    fn name(&self) -> &'static str {
        "commonfeed"
    }

    fn collect(
        &self,
        limit: usize,
    ) -> Pin<Box<dyn Future<Output = Vec<Candidate<Post>>> + Send + '_>> {
        Box::pin(async move {
            let response = super::fetch_json::<QueryResponse>(
                &self.provider,
                "posts",
                &self.algorithm,
                &self.filters,
                limit,
            )
            .await;

            match response {
                Some(r) => r.results.into_iter().map(into_candidate).collect(),
                None => Vec::new(),
            }
        })
    }
}

fn into_candidate(result: PostResult) -> Candidate<Post> {
    let engagement = result.engagement.as_ref();

    let media = result
        .media
        .unwrap_or_default()
        .into_iter()
        .map(|m| Media {
            media_type: m.media_type,
            url: m.url,
            alt: m.alt,
            mime_type: m.mime_type,
            width: m.width,
            height: m.height,
            blurhash: m.blurhash,
            thumbnail_url: m.thumbnail_url,
        })
        .collect();

    let post = Post {
        url: result.url,
        content: result.content,
        text: result.text,
        author: Author {
            handle: result.author.handle,
            display_name: result.author.name,
            url: result.author.url,
            avatar_url: result.author.avatar_url,
        },
        published_at: result.timestamp,
        language: result.language,
        sensitive: result.sensitive.unwrap_or(false),
        content_warning: result.content_warning,
        media,
        engagement: Engagement {
            replies: engagement.and_then(|e| e.replies).unwrap_or(0),
            reposts: engagement.and_then(|e| e.reposts).unwrap_or(0),
            likes: engagement.and_then(|e| e.likes).unwrap_or(0),
        },
        reply_to: result.reply_to,
        quote_url: result.quote_url,
    };

    let mut candidate = Candidate::new(post, "commonfeed");
    candidate.score = result.score.unwrap_or(0.0);
    candidate
}

#[cfg(test)]
mod tests {
    use super::super::types::{AuthorResult, EngagementResult};
    use super::*;

    #[test]
    fn converts_post_result_to_candidate() {
        let result = PostResult {
            url: "https://mastodon.social/@alice/123".to_string(),
            protocol: "activitypub".to_string(),
            content_type: "post".to_string(),
            content: "<p>hello</p>".to_string(),
            text: "hello".to_string(),
            author: AuthorResult {
                name: "Alice".to_string(),
                handle: "@alice@mastodon.social".to_string(),
                url: "https://mastodon.social/@alice".to_string(),
                avatar_url: None,
            },
            timestamp: chrono::Utc::now(),
            language: Some("en".to_string()),
            sensitive: None,
            content_warning: None,
            media: None,
            engagement: Some(EngagementResult {
                likes: Some(42),
                reposts: Some(10),
                replies: Some(5),
            }),
            reply_to: None,
            quote_url: None,
            score: Some(0.85),
        };

        let candidate = into_candidate(result);
        assert_eq!(candidate.item.text, "hello");
        assert_eq!(candidate.item.author.display_name, "Alice");
        assert_eq!(candidate.item.engagement.likes, 42);
        assert_eq!(candidate.item.engagement.reposts, 10);
        assert_eq!(candidate.item.engagement.replies, 5);
        assert_eq!(candidate.score, 0.85);
        assert_eq!(candidate.source, "commonfeed");
    }

    #[test]
    fn handles_missing_engagement() {
        let result = PostResult {
            url: "https://example.com/post/1".to_string(),
            protocol: "activitypub".to_string(),
            content_type: "post".to_string(),
            content: "<p>test</p>".to_string(),
            text: "test".to_string(),
            author: AuthorResult {
                name: "Bob".to_string(),
                handle: "@bob@example.com".to_string(),
                url: "https://example.com/@bob".to_string(),
                avatar_url: None,
            },
            timestamp: chrono::Utc::now(),
            language: None,
            sensitive: None,
            content_warning: None,
            media: None,
            engagement: None,
            reply_to: None,
            quote_url: None,
            score: None,
        };

        let candidate = into_candidate(result);
        assert_eq!(candidate.item.engagement.likes, 0);
        assert_eq!(candidate.item.engagement.reposts, 0);
        assert_eq!(candidate.item.engagement.replies, 0);
        assert_eq!(candidate.score, 0.0);
    }

    #[test]
    fn filters_serialize_correctly() {
        let filters = QueryFilters {
            language: vec!["en".to_string(), "de".to_string()],
            ..Default::default()
        };
        let json = serde_json::to_value(&filters).unwrap();
        assert_eq!(json, serde_json::json!({"language": ["en", "de"]}));
    }

    #[test]
    fn empty_filters_serialize_empty() {
        let filters = QueryFilters::default();
        let json = serde_json::to_value(&filters).unwrap();
        assert_eq!(json, serde_json::json!({}));
    }

    #[test]
    fn for_provider_includes_supported_filters() {
        let filters = QueryFilters {
            language: vec!["en".to_string()],
            ..Default::default()
        };
        let supported = vec!["language".to_string(), "protocol".to_string()];
        let result = filters.for_provider(&supported);
        assert_eq!(result.language, vec!["en"]);
    }

    #[test]
    fn for_provider_excludes_unsupported_filters() {
        let filters = QueryFilters {
            language: vec!["en".to_string()],
            ..Default::default()
        };
        let supported: Vec<String> = vec!["protocol".to_string()];
        let result = filters.for_provider(&supported);
        assert!(result.language.is_empty());
    }
}
