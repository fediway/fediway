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

pub(super) fn into_candidate(result: super::types::TagResult) -> Candidate<types::Tag> {
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

#[cfg(test)]
mod tests {
    use super::super::types::{TagHistoryItem, TagResult};
    use super::*;

    #[test]
    fn converts_tag_result_to_candidate() {
        let result = TagResult {
            name: "rust".into(),
            post_count: 42,
            account_count: 15,
            history: Some(vec![TagHistoryItem {
                day: "1709251200".into(),
                uses: 30,
                accounts: 12,
            }]),
            score: Some(0.95),
        };
        let candidate = into_candidate(result);
        assert_eq!(candidate.item.name, "rust");
        assert_eq!(candidate.item.url, "/tags/rust");
        assert_eq!(candidate.item.history.len(), 1);
        assert_eq!(candidate.item.history[0].uses, 30);
        assert_eq!(candidate.item.history[0].accounts, 12);
        assert_eq!(candidate.source, "commonfeed");
    }

    #[test]
    fn uses_score_from_result() {
        let result = TagResult {
            name: "test".into(),
            post_count: 1,
            account_count: 1,
            history: None,
            score: Some(0.75),
        };
        let candidate = into_candidate(result);
        assert!((candidate.score - 0.75).abs() < f64::EPSILON);
    }

    #[test]
    fn defaults_score_to_zero() {
        let result = TagResult {
            name: "test".into(),
            post_count: 1,
            account_count: 1,
            history: None,
            score: None,
        };
        let candidate = into_candidate(result);
        assert!((candidate.score).abs() < f64::EPSILON);
    }

    #[test]
    fn handles_missing_history() {
        let result = TagResult {
            name: "fediverse".into(),
            post_count: 5,
            account_count: 3,
            history: None,
            score: None,
        };
        let candidate = into_candidate(result);
        assert!(candidate.item.history.is_empty());
    }
}
