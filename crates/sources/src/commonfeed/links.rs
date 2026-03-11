use std::future::Future;
use std::pin::Pin;

use common::types::{self, Provider};
use feed::candidate::Candidate;
use feed::source::Source;

use super::types::{LinkResponse, QueryFilters};

pub struct LinksSource {
    algorithm: String,
    provider: Provider,
    filters: QueryFilters,
}

impl LinksSource {
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

impl Source<types::Link> for LinksSource {
    fn name(&self) -> &'static str {
        "commonfeed/links"
    }

    fn collect(
        &self,
        limit: usize,
    ) -> Pin<Box<dyn Future<Output = Vec<Candidate<types::Link>>> + Send + '_>> {
        Box::pin(async move {
            let response = super::fetch_json::<LinkResponse>(
                &self.provider,
                "links",
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

pub(super) fn into_candidate(result: super::types::LinkResult) -> Candidate<types::Link> {
    let score = result.score.unwrap_or(0.0);

    let link = types::Link {
        url: result.url,
        title: result.title,
        description: result.description,
        link_type: result.link_type,
        author_name: result.author_name,
        provider_name: result.provider_name,
        image_url: result.image_url,
        image_width: result.image_width,
        image_height: result.image_height,
        blurhash: result.blurhash,
        embed_url: result.embed_url,
    };

    let mut candidate = Candidate::new(link, "commonfeed/links");
    candidate.score = score;
    candidate
}

#[cfg(test)]
mod tests {
    use super::super::types::LinkResult;
    use super::*;

    fn sample_link_result() -> LinkResult {
        LinkResult {
            url: "https://example.com/article".into(),
            title: "Example".into(),
            description: "A great article".into(),
            link_type: "link".into(),
            image_url: Some("https://cdn.example/og.webp".into()),
            image_width: Some(1200),
            image_height: Some(630),
            blurhash: Some("LEHV6nWB2yk8".into()),
            provider_name: Some("Example News".into()),
            author_name: Some("Alice".into()),
            embed_html: None,
            embed_url: None,
            embed_width: None,
            embed_height: None,
            language: Some("en".into()),
            published_at: None,
            favicon_url: None,
            favicon_blurhash: None,
            post_count: Some(42),
            account_count: Some(15),
            score: Some(0.8),
        }
    }

    #[test]
    fn converts_link_result_to_candidate() {
        let candidate = into_candidate(sample_link_result());
        assert_eq!(candidate.item.url, "https://example.com/article");
        assert_eq!(candidate.item.title, "Example");
        assert_eq!(candidate.item.link_type, "link");
        assert_eq!(candidate.item.author_name.as_deref(), Some("Alice"));
        assert_eq!(
            candidate.item.provider_name.as_deref(),
            Some("Example News")
        );
        assert_eq!(candidate.item.image_width, Some(1200));
        assert_eq!(candidate.source, "commonfeed/links");
    }

    #[test]
    fn uses_score_from_result() {
        let candidate = into_candidate(sample_link_result());
        assert!((candidate.score - 0.8).abs() < f64::EPSILON);
    }

    #[test]
    fn defaults_score_to_zero() {
        let result = LinkResult {
            score: None,
            ..sample_link_result()
        };
        let candidate = into_candidate(result);
        assert!((candidate.score).abs() < f64::EPSILON);
    }

    #[test]
    fn handles_minimal_link() {
        let result = LinkResult {
            image_url: None,
            image_width: None,
            image_height: None,
            blurhash: None,
            provider_name: None,
            author_name: None,
            embed_url: None,
            score: None,
            ..sample_link_result()
        };
        let candidate = into_candidate(result);
        assert!(candidate.item.image_url.is_none());
        assert!(candidate.item.author_name.is_none());
        assert!(candidate.item.provider_name.is_none());
    }
}
