use std::time::Instant;

use axum::Json;
use axum::http::{HeaderMap, HeaderValue, header};
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
use sources::mastodon::{CachedPost, NetworkSource, PolicyFilter};

use crate::auth::Account;
use crate::feeds::timeline_feed::TimelineParams;
use crate::state::AppState;

const POOL_SIZE: usize = 300;
const NETWORK_POOL: usize = 180;
const RECOMMENDED_POOL: usize = 180;
const TRENDING_POOL_COLD: usize = 300;
const TRENDING_POOL_WARM: usize = 60;

pub struct HomeFeed {
    pipeline: Pipeline<Post>,
    user_id: i64,
}

impl HomeFeed {
    pub async fn new(state: &AppState, account: &Account, filters: QueryFilters) -> Self {
        let vector_start = Instant::now();
        let (user_vector, policy) = tokio::join!(
            state::orbit::load_vector(&state.pool, account.id),
            state::policy::load(&state.pool, account.id, &state.instance_domain),
        );
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

        let has_vector = user_vector.is_some();
        let recommended_pool = if has_vector { RECOMMENDED_POOL } else { 0 };
        let trending_pool = if has_vector {
            TRENDING_POOL_WARM
        } else {
            TRENDING_POOL_COLD
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
                state.media.clone(),
            )],
            NETWORK_POOL,
        );

        let trending = state::providers::find_sources(&state.pool, "trends/statuses").await;
        let trending_sources = trending
            .into_iter()
            .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));
        builder = builder.group("trending", trending_sources, trending_pool);

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
        }

        let trending_quota = if has_vector {
            GroupQuota::new("trending").cap(0.10)
        } else {
            GroupQuota::new("trending")
        };

        let pipeline = builder
            .filter(Dedup::new(|c: &Candidate<Post>| c.item.url.clone()))
            .filter(PolicyFilter::new(policy))
            .score(Diversity::new(0.15, |post: &Post| {
                post.author.handle.clone()
            }))
            .sampler(QuotaSampler::new([
                GroupQuota::new("network").min(12).cap(0.60),
                GroupQuota::new("recommended").cap(0.40),
                trending_quota,
            ]))
            .build();

        Self {
            pipeline,
            user_id: account.id,
        }
    }

    pub async fn serve(
        &self,
        state: &AppState,
        params: &TimelineParams,
    ) -> (HeaderMap, Json<Vec<Status>>) {
        let start = Instant::now();
        metrics::counter!("fediway_home_requests_total").increment(1);

        let cache_key = format!("home:{}", self.user_id);
        let limit = params.limit.clamp(1, 40);

        // The home feed is ranked, not chronological, so `min_id` and
        // `since_id` have no meaning here — the entire ordering is rebuilt
        // each pipeline run. We commandeer `max_id` as an opaque offset
        // into the cached scored list because Mastodon's API exposes no
        // other cursor field.
        let page = state
            .feed_store
            .page(&cache_key, params.max_id.as_deref(), limit, || async {
                self.collect()
                    .await
                    .into_iter()
                    .map(|c| CachedPost::from_post(c.item, &state.instance_domain))
                    .collect::<Vec<CachedPost>>()
            })
            .await;

        let statuses = crate::mastodon::statuses::hydrate(
            &state.pool,
            &state.instance_domain,
            &state.media,
            page.items,
            Some(self.user_id),
        )
        .await;

        let mut headers = HeaderMap::new();
        if let Some(next) = &page.cursor {
            let link = format!(
                "<https://{}/api/v1/timelines/home?max_id={next}>; rel=\"next\"",
                state.instance_domain
            );
            if let Ok(value) = HeaderValue::from_str(&link) {
                headers.insert(header::LINK, value);
            }
        }

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
