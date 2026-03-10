use std::future::Future;
use std::pin::Pin;

use common::types::{self, Provider};
use pipeline::candidate::Candidate;
use pipeline::source::Source;

use super::types::{QueryFilters, TagResponse};

pub struct TagsSource {
    algorithm: String,
    provider: Provider,
    filters: QueryFilters,
}

impl TagsSource {
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

impl Source<types::Tag> for TagsSource {
    fn name(&self) -> &'static str {
        "commonfeed"
    }

    fn collect(
        &self,
        limit: usize,
    ) -> Pin<Box<dyn Future<Output = Vec<Candidate<types::Tag>>> + Send + '_>> {
        Box::pin(async move {
            let response = super::fetch_json::<TagResponse>(
                &self.provider,
                "tags",
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

fn into_candidate(result: super::types::TagResult) -> Candidate<types::Tag> {
    let score = result.score.unwrap_or(0.0);

    let history = result
        .history
        .unwrap_or_default()
        .into_iter()
        .map(|h| types::TagHistory {
            day: h.day,
            uses: h.uses,
            accounts: h.accounts,
        })
        .collect();

    let tag = types::Tag {
        name: result.name.clone(),
        url: format!("/tags/{}", result.name),
        history,
    };

    let mut candidate = Candidate::new(tag, "commonfeed");
    candidate.score = score;
    candidate
}
