use common::types::{Post, Provider};
use feed::candidate::Candidate;
use feed::source::Source;

use super::posts::into_candidate_with_source;
use super::types::{EmbeddingRequest, QueryFilters, QueryResponse};

pub struct RecommendedSource {
    provider: Provider,
    algorithm: String,
    filters: QueryFilters,
    embedding: EmbeddingRequest,
}

impl RecommendedSource {
    #[must_use]
    pub fn new(
        provider: Provider,
        algorithm: impl Into<String>,
        vector: Vec<f32>,
        model: impl Into<String>,
    ) -> Self {
        Self {
            provider,
            algorithm: algorithm.into(),
            filters: QueryFilters::default(),
            embedding: EmbeddingRequest {
                vector,
                model: model.into(),
            },
        }
    }

    #[must_use]
    pub fn with_filters(mut self, filters: QueryFilters) -> Self {
        self.filters = filters;
        self
    }
}

#[async_trait::async_trait]
impl Source<Post> for RecommendedSource {
    fn name(&self) -> &'static str {
        "commonfeed/recommended"
    }

    async fn collect(&self, limit: usize) -> Vec<Candidate<Post>> {
        let response = super::fetch_json::<QueryResponse>(
            &self.provider,
            "posts",
            &self.algorithm,
            &self.filters,
            Some(&self.embedding),
            limit,
        )
        .await;

        let domain = &self.provider.domain;
        match response {
            Some(r) => r
                .results
                .into_iter()
                .map(|r| into_candidate_with_source(r, domain, "commonfeed/recommended"))
                .collect(),
            None => Vec::new(),
        }
    }
}
