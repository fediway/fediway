use std::time::{Duration, Instant};

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

use crate::feeds::seen;
use crate::feeds::timeline_feed::TimelineParams;
use crate::state::AppState;

const HOME_TTL: Duration = Duration::from_secs(15 * 60);

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
    pub async fn new(state: &AppState, user_id: i64, filters: QueryFilters) -> Self {
        let vector_start = Instant::now();
        let (user_vector, policy) = tokio::join!(
            state::orbit::load_vector(&state.pool, user_id),
            state::policy::load(&state.pool, user_id, &state.instance_domain),
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
                user_id,
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

        let pipeline = builder
            .filter(Dedup::new(|c: &Candidate<Post>| {
                c.item.uri.clone().unwrap_or_else(|| c.item.url.clone())
            }))
            .filter(PolicyFilter::new(policy))
            .score(Diversity::new(0.15, |post: &Post| {
                post.author.handle.clone()
            }))
            .sampler(if has_vector {
                QuotaSampler::new([
                    GroupQuota::new("network", 0.60),
                    GroupQuota::new("recommended", 0.30),
                    GroupQuota::new("trending", 0.10),
                ])
            } else {
                QuotaSampler::new([
                    GroupQuota::new("network", 0.70),
                    GroupQuota::new("trending", 0.30),
                ])
            })
            .build();

        Self { pipeline, user_id }
    }

    pub async fn serve(
        &self,
        state: &AppState,
        params: &TimelineParams,
    ) -> (HeaderMap, Json<Vec<Status>>) {
        let start = Instant::now();
        metrics::counter!("fediway_home_requests_total").increment(1);

        let limit = params.limit.clamp(1, 40);

        // The home feed is ranked, not chronological. The server tracks
        // per-user seen identifiers and filters them from the ranked pool,
        // so `max_id`/`min_id`/`since_id` are ignored — any request means
        // "give me the next unseen slice." The ActivityPub URI (with URL
        // fallback) is the stable identity; snowflake IDs shift when
        // remote posts get promoted to Mastodon local IDs. See `feeds::seen`.
        let pool = self.load_pool(state).await;
        let seen_set = seen::load(&state.cache, self.user_id).await;

        let (served, cached_posts): (Vec<String>, Vec<CachedPost>) = pool
            .into_iter()
            .filter(|(id, _)| !seen_set.contains(id))
            .take(limit)
            .unzip();

        let statuses = crate::mastodon::statuses::hydrate(
            &state.pool,
            &state.instance_domain,
            &state.media,
            cached_posts,
            Some(self.user_id),
        )
        .await;

        seen::extend(&state.cache, self.user_id, &served).await;

        let mut headers = HeaderMap::new();
        if let Some(last) = statuses.last() {
            let link = format!(
                "<https://{}/api/v1/timelines/home?max_id={}>; rel=\"next\"",
                state.instance_domain, last.id,
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

    async fn load_pool(&self, state: &AppState) -> Vec<(String, CachedPost)> {
        let key = format!("home:{}", self.user_id);
        if let Some(pool) = state.cache.get::<Vec<(String, CachedPost)>>(&key).await
            && !pool.is_empty()
        {
            return pool;
        }
        let pool: Vec<_> = self
            .collect()
            .await
            .into_iter()
            .map(|c| {
                let id = c.item.uri.clone().unwrap_or_else(|| c.item.url.clone());
                (id, CachedPost::from_post(c.item, &state.instance_domain))
            })
            .collect();
        state.cache.set(&key, &pool, HOME_TTL).await;
        pool
    }
}

impl Feed for HomeFeed {
    type Item = Post;

    async fn collect(&self) -> Vec<Candidate<Post>> {
        self.pipeline.execute(POOL_SIZE, &()).await.items
    }
}
