use std::future::Future;
use std::pin::Pin;

use common::types::{self, Provider};
use pipeline::candidate::Candidate;
use pipeline::source::Source;

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
        "commonfeed"
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

fn into_candidate(result: super::types::LinkResult) -> Candidate<types::Link> {
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

    let mut candidate = Candidate::new(link, "commonfeed");
    candidate.score = score;
    candidate
}
