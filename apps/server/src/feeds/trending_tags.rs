use common::types::Tag;
use feed::Feed;
use feed::candidate::Candidate;
use feed::pipeline::Pipeline;
use feed::scorer::Diversity;
use mastodon::Tag as MastodonTag;
use sources::commonfeed::tags::TagsSource;
use sources::commonfeed::types::QueryFilters;

use crate::feeds::trend_feed::TrendFeed;
use crate::state::AppState;

const POOL_SIZE: usize = 100;

pub struct TrendingTagsFeed {
    pipeline: Pipeline<Tag>,
}

impl TrendingTagsFeed {
    pub async fn new(state: &AppState, filters: QueryFilters) -> Self {
        let bound = state::providers::find_sources(&state.pool, "trends/tags").await;
        let sources = bound
            .into_iter()
            .map(|b| TagsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

        let pipeline = Pipeline::builder()
            .name("trends/tags")
            .sources(sources, POOL_SIZE)
            .score(Diversity::new(0.1, |tag: &Tag| tag.name.clone()))
            .build();

        Self { pipeline }
    }
}

impl Feed for TrendingTagsFeed {
    type Item = Tag;

    async fn collect(&self) -> Vec<Candidate<Tag>> {
        self.pipeline.execute(POOL_SIZE, &()).await.items
    }
}

impl TrendFeed for TrendingTagsFeed {
    type Response = MastodonTag;
    const RESOURCE: &'static str = "tags";
    const PATH: &'static str = "/api/v1/trends/tags";

    async fn map(&self, _state: &AppState, items: Vec<Tag>) -> Vec<MastodonTag> {
        items.into_iter().map(MastodonTag::from).collect()
    }
}
