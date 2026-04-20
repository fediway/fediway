use std::future::Future;
use std::pin::Pin;

use common::types::Post;
use feed::Feed;
use feed::candidate::Candidate;
use feed::filter::Dedup;
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
    filters: QueryFilters,
}

impl TrendingStatusesFeed {
    pub async fn new(state: &AppState, filters: QueryFilters) -> Self {
        let bound = state::providers::find_sources(&state.pool, "trends/statuses")
            .await
            .unwrap_or_else(|err| {
                tracing::error!(error = %err, route = "trends/statuses", "failed to load sources");
                Vec::new()
            });
        let sources = bound
            .into_iter()
            .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

        let pipeline = Pipeline::builder()
            .name("trends/statuses")
            .sources(sources, POOL_SIZE)
            .filter(Dedup::new(|c: &Candidate<Post>| c.item.url.clone()))
            .score(Diversity::new(0.1, |post: &Post| {
                post.author.handle.clone()
            }))
            .build();

        Self { pipeline, filters }
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

    fn cache_key(&self) -> String {
        let mut langs = self.filters.language.clone();
        langs.sort();
        let lang = if langs.is_empty() {
            "*".to_owned()
        } else {
            langs.join(",")
        };
        format!("trends:statuses:{lang}")
    }

    async fn map(&self, state: &AppState, items: Vec<Post>) -> Vec<Status> {
        crate::mastodon::statuses::from_posts(&state.pool, &state.instance_domain, items).await
    }

    fn rebuild(&self, state: &AppState) -> Pin<Box<dyn Future<Output = Vec<Post>> + Send>> {
        let state = state.clone();
        let filters = self.filters.clone();
        Box::pin(async move {
            let feed = TrendingStatusesFeed::new(&state, filters).await;
            feed.collect().await.into_iter().map(|c| c.item).collect()
        })
    }
}
