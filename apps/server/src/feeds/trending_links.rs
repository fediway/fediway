use std::future::Future;
use std::pin::Pin;

use common::types::Link;
use feed::Feed;
use feed::candidate::Candidate;
use feed::filter::Dedup;
use feed::pipeline::Pipeline;
use feed::scorer::Diversity;
use mastodon::PreviewCard;
use sources::commonfeed::links::LinksSource;
use sources::commonfeed::types::QueryFilters;

use crate::feeds::trend_feed::TrendFeed;
use crate::state::AppState;

const FETCH_POOL: usize = 100;
const MAX_RESULTS: usize = 7;

pub struct TrendingLinksFeed {
    pipeline: Pipeline<Link>,
    filters: QueryFilters,
}

impl TrendingLinksFeed {
    pub async fn new(state: &AppState, filters: QueryFilters) -> Self {
        let bound = state::providers::find_sources(&state.pool, "trends/links")
            .await
            .unwrap_or_else(|err| {
                tracing::error!(error = %err, route = "trends/links", "failed to load sources");
                Vec::new()
            });
        let sources = bound
            .into_iter()
            .map(|b| LinksSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

        let pipeline = Pipeline::builder()
            .name("trends/links")
            .sources(sources, FETCH_POOL)
            .filter(Dedup::new(|c: &Candidate<Link>| c.item.url.clone()))
            .score(Diversity::new(0.1, |link: &Link| {
                link.provider_name.clone().unwrap_or_default()
            }))
            .build();

        Self { pipeline, filters }
    }
}

impl Feed for TrendingLinksFeed {
    type Item = Link;

    async fn collect(&self) -> Vec<Candidate<Link>> {
        self.pipeline.execute(MAX_RESULTS, &()).await.items
    }
}

impl TrendFeed for TrendingLinksFeed {
    type Response = PreviewCard;
    const RESOURCE: &'static str = "links";
    const PATH: &'static str = "/api/v1/trends/links";

    fn cache_key(&self) -> String {
        let mut langs = self.filters.language.clone();
        langs.sort();
        let lang = if langs.is_empty() {
            "*".to_owned()
        } else {
            langs.join(",")
        };
        format!("trends:links:{lang}")
    }

    async fn map(&self, _state: &AppState, items: Vec<Link>) -> Vec<PreviewCard> {
        items.into_iter().map(PreviewCard::from).collect()
    }

    fn rebuild(&self, state: &AppState) -> Pin<Box<dyn Future<Output = Vec<Link>> + Send>> {
        let state = state.clone();
        let filters = self.filters.clone();
        Box::pin(async move {
            let feed = TrendingLinksFeed::new(&state, filters).await;
            feed.collect().await.into_iter().map(|c| c.item).collect()
        })
    }
}
