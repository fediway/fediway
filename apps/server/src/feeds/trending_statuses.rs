use common::types::Post;
use feed::Feed;
use feed::candidate::Candidate;
use feed::pipeline::Pipeline;
use feed::scorer::Diversity;
use mastodon::Status;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::types::QueryFilters;

use crate::feeds::trend_feed::TrendFeed;
use crate::state::AppState;

const POOL_SIZE: usize = 100;

pub struct TrendingStatusesFeed {
    pipeline: Pipeline<Post>,
}

impl TrendingStatusesFeed {
    pub async fn new(state: &AppState, filters: QueryFilters) -> Self {
        let bound = state::providers::find_sources(&state.pool, "trends/statuses").await;
        let sources = bound
            .into_iter()
            .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

        let pipeline = Pipeline::builder()
            .name("trends/statuses")
            .sources(sources, POOL_SIZE)
            .score(Diversity::new(0.1, |post: &Post| {
                post.author.handle.clone()
            }))
            .build();

        Self { pipeline }
    }
}

impl Feed for TrendingStatusesFeed {
    type Item = Post;

    async fn collect(&self) -> Vec<Candidate<Post>> {
        self.pipeline.execute(POOL_SIZE, &()).await.items
    }
}

impl TrendFeed for TrendingStatusesFeed {
    type Response = Status;
    const RESOURCE: &'static str = "statuses";
    const PATH: &'static str = "/api/v1/trends/statuses";

    async fn map(&self, state: &AppState, items: Vec<Post>) -> Vec<Status> {
        crate::mastodon::statuses::from_posts(&state.pool, items).await
    }
}
