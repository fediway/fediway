use common::types::Post;
use feed::Feed;
use feed::candidate::Candidate;
use feed::filter::Dedup;
use feed::pipeline::Pipeline;
use feed::scorer::Diversity;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::recommended::RecommendedSource;
use sources::commonfeed::types::QueryFilters;

use crate::auth::Account;
use crate::state::AppState;

const POOL_SIZE: usize = 100;

pub struct HomeFeed {
    pipeline: Pipeline<Post>,
}

impl HomeFeed {
    pub async fn new(state: &AppState, account: &Account, filters: QueryFilters) -> Self {
        let vector_start = std::time::Instant::now();
        let user_vector = state::orbit::load_vector(&state.pool, account.id).await;
        metrics::histogram!("fediway_home_vector_load_duration_seconds")
            .record(vector_start.elapsed().as_secs_f64());

        let (recommended_pool, trending_pool) = if let Some((_, count)) = &user_vector {
            metrics::counter!("fediway_home_vector_loaded_total", "result" => "found").increment(1);
            let confidence = (f64::from(i32::try_from(*count).unwrap_or(i32::MAX)) / 50.0).min(1.0);
            metrics::histogram!("fediway_home_confidence").record(confidence);
            (POOL_SIZE, 0)
        } else {
            metrics::counter!("fediway_home_vector_loaded_total", "result" => "cold_start")
                .increment(1);
            (0, 0)
        };

        #[allow(clippy::cast_precision_loss)]
        metrics::histogram!("fediway_home_recommended_pool").record(recommended_pool as f64);
        #[allow(clippy::cast_precision_loss)]
        metrics::histogram!("fediway_home_trending_pool").record(trending_pool as f64);

        let mut builder = Pipeline::builder().name("timelines/home");

        if let Some((vector, _)) = &user_vector
            && recommended_pool > 0
        {
            let bound = state::providers::find_sources(&state.pool, "timelines/home").await;
            for b in bound {
                builder = builder.source(
                    RecommendedSource::new(
                        b.provider,
                        b.algorithm,
                        vector.clone(),
                        &state.orbit_model_name,
                    )
                    .with_filters(filters.clone()),
                    recommended_pool,
                );
            }
        }

        let trending = state::providers::find_sources(&state.pool, "trends/statuses").await;
        for b in trending {
            builder = builder.source(
                PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()),
                trending_pool,
            );
        }

        let pipeline = builder
            .filter(Dedup::new(|post: &Post| post.url.clone()))
            .score(Diversity::new(0.15, |post: &Post| {
                post.author.handle.clone()
            }))
            .build();

        Self { pipeline }
    }
}

impl Feed for HomeFeed {
    type Item = Post;

    async fn collect(&self) -> Vec<Candidate<Post>> {
        self.pipeline.execute(POOL_SIZE, &()).await.items
    }
}
