use common::types::Link;
use feed::Feed;
use feed::candidate::Candidate;
use feed::pipeline::Pipeline;
use feed::scorer::Diversity;
use mastodon::PreviewCard;
use sources::commonfeed::links::LinksSource;
use sources::commonfeed::types::QueryFilters;

use crate::feeds::trend_feed::TrendFeed;
use crate::state::AppState;

const POOL_SIZE: usize = 100;

pub struct TrendingLinksFeed {
    pipeline: Pipeline<Link>,
}

impl TrendingLinksFeed {
    pub async fn new(state: &AppState, filters: QueryFilters) -> Self {
        let bound = state::providers::find_sources(&state.pool, "trends/links").await;
        let sources = bound
            .into_iter()
            .map(|b| LinksSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

        let pipeline = Pipeline::builder()
            .name("trends/links")
            .sources(sources, POOL_SIZE)
            .score(Diversity::new(0.1, |link: &Link| {
                link.provider_name.clone().unwrap_or_default()
            }))
            .build();

        Self { pipeline }
    }
}

impl Feed for TrendingLinksFeed {
    type Item = Link;

    async fn collect(&self) -> Vec<Candidate<Link>> {
        self.pipeline.execute(POOL_SIZE, &()).await.items
    }
}

impl TrendFeed for TrendingLinksFeed {
    type Response = PreviewCard;
    const RESOURCE: &'static str = "links";
    const PATH: &'static str = "/api/v1/trends/links";

    async fn map(&self, _state: &AppState, items: Vec<Link>) -> Vec<PreviewCard> {
        items.into_iter().map(PreviewCard::from).collect()
    }
}
