use std::time::Instant;

use axum::Json;
use axum::http::HeaderMap;
use common::types::Post;
use feed::Feed;
use feed::candidate::Candidate;
use feed::filter::Dedup;
use feed::pipeline::Pipeline;
use feed::quota_sampler::{GroupQuota, QuotaSampler};
use feed::scorer::Diversity;
use mastodon::Status;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::recommended::RecommendedSource;
use sources::commonfeed::types::QueryFilters;
use sources::mastodon::NetworkSource;

use crate::auth::Account;
use crate::feeds::timeline_feed::TimelineParams;
use crate::state::AppState;

const POOL_SIZE: usize = 100;
const NETWORK_POOL: usize = 60;
const RECOMMENDED_POOL: usize = 60;
const TRENDING_POOL: usize = 100;

pub struct HomeFeed {
    pipeline: Pipeline<Post>,
}

impl HomeFeed {
    pub async fn new(state: &AppState, account: &Account, filters: QueryFilters) -> Self {
        let vector_start = Instant::now();
        let user_vector = state::orbit::load_vector(&state.pool, account.id).await;
        metrics::histogram!("fediway_home_vector_load_duration_seconds")
            .record(vector_start.elapsed().as_secs_f64());

        if let Some((_, count)) = &user_vector {
            metrics::counter!("fediway_home_vector_loaded_total", "result" => "found").increment(1);
            let confidence = (f64::from(i32::try_from(*count).unwrap_or(i32::MAX)) / 50.0).min(1.0);
            metrics::histogram!("fediway_home_confidence").record(confidence);
        } else {
            metrics::counter!("fediway_home_vector_loaded_total", "result" => "cold_start")
                .increment(1);
        }

        let (recommended_pool, trending_pool) = if user_vector.is_some() {
            (RECOMMENDED_POOL, 0)
        } else {
            (0, TRENDING_POOL)
        };

        #[allow(clippy::cast_precision_loss)]
        metrics::histogram!("fediway_home_network_pool").record(NETWORK_POOL as f64);
        #[allow(clippy::cast_precision_loss)]
        metrics::histogram!("fediway_home_recommended_pool").record(recommended_pool as f64);
        #[allow(clippy::cast_precision_loss)]
        metrics::histogram!("fediway_home_trending_pool").record(trending_pool as f64);

        let mut builder = Pipeline::builder().name("timelines/home").group(
            "network",
            [NetworkSource::new(
                state.pool.clone(),
                account.id,
                state.instance_domain.clone(),
            )],
            NETWORK_POOL,
        );

        if let Some((vector, _)) = &user_vector {
            let bound = state::providers::find_sources(&state.pool, "timelines/home").await;
            let recommended = bound.into_iter().map(|b| {
                RecommendedSource::new(
                    b.provider,
                    b.algorithm,
                    vector.clone(),
                    &state.orbit_model_name,
                )
                .with_filters(filters.clone())
            });
            builder = builder.group("recommended", recommended, RECOMMENDED_POOL);
        } else {
            let trending = state::providers::find_sources(&state.pool, "trends/statuses").await;
            let trending_sources = trending
                .into_iter()
                .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));
            builder = builder.group("trending", trending_sources, TRENDING_POOL);
        }

        let pipeline = builder
            .filter(Dedup::new(|c: &Candidate<Post>| c.item.url.clone()))
            .score(Diversity::new(0.15, |post: &Post| {
                post.author.handle.clone()
            }))
            .sampler(QuotaSampler::new([
                GroupQuota::new("network").min(12).cap(0.60),
                GroupQuota::new("recommended").cap(0.40),
                GroupQuota::new("trending"),
            ]))
            .build();

        Self { pipeline }
    }

    pub async fn serve(
        &self,
        state: &AppState,
        params: &TimelineParams,
    ) -> (HeaderMap, Json<Vec<Status>>) {
        let start = Instant::now();
        metrics::counter!("fediway_home_requests_total").increment(1);

        let candidates = self.collect().await;
        let posts: Vec<Post> = candidates.into_iter().map(|c| c.item).collect();
        let statuses =
            crate::mastodon::statuses::from_posts(&state.pool, &state.instance_domain, posts).await;

        let (statuses, headers) = crate::mastodon::statuses::paginate(
            statuses,
            params.limit.min(40),
            params.max_id.as_deref(),
            params.min_id.as_deref(),
            params.since_id.as_deref(),
            &state.instance_domain,
            "/api/v1/timelines/home",
        );

        #[allow(clippy::cast_precision_loss)]
        metrics::histogram!("fediway_home_results").record(statuses.len() as f64);
        metrics::histogram!("fediway_home_duration_seconds").record(start.elapsed().as_secs_f64());

        (headers, Json(statuses))
    }
}

impl Feed for HomeFeed {
    type Item = Post;

    async fn collect(&self) -> Vec<Candidate<Post>> {
        self.pipeline.execute(POOL_SIZE, &()).await.items
    }
}
