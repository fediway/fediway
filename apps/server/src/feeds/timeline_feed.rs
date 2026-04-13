use std::borrow::Cow;
use std::time::Instant;

use axum::Json;
use axum::http::HeaderMap;
use common::types::Post;
use feed::Feed;
use mastodon::Status;
use serde::Deserialize;

use crate::mastodon::statuses;
use crate::state::AppState;

/// Supertrait for Mastodon timeline endpoints: `home`, `tag(hashtag)`,
/// `link(url)`. All produce `Vec<Status>` and paginate by Mastodon
/// keyset (`max_id`/`min_id`/`since_id`) over the built statuses, not
/// by cursor over raw candidates — which is why they need a supertrait
/// distinct from `TrendFeed`.
pub trait TimelineFeed: Feed<Item = Post> {
    const RESOURCE: &'static str;

    fn path(&self) -> Cow<'static, str>;

    fn serve(
        &self,
        state: &AppState,
        params: &TimelineParams,
    ) -> impl std::future::Future<Output = (HeaderMap, Json<Vec<Status>>)> + Send {
        async move {
            let start = Instant::now();
            metrics::counter!("fediway_timelines_requests_total", "resource" => Self::RESOURCE)
                .increment(1);

            let candidates = self.collect().await;
            let posts: Vec<Post> = candidates.into_iter().map(|c| c.item).collect();
            let built = statuses::from_posts(&state.pool, &state.instance_domain, posts).await;
            let (page, headers) = statuses::paginate(
                built,
                params.limit.min(40),
                params.max_id.as_deref(),
                params.min_id.as_deref(),
                params.since_id.as_deref(),
                &state.instance_domain,
                &self.path(),
            );

            #[allow(clippy::cast_precision_loss)]
            metrics::histogram!("fediway_timelines_results", "resource" => Self::RESOURCE)
                .record(page.len() as f64);
            metrics::histogram!("fediway_timelines_duration_seconds", "resource" => Self::RESOURCE)
                .record(start.elapsed().as_secs_f64());

            (headers, Json(page))
        }
    }
}

#[derive(Deserialize)]
pub struct TimelineParams {
    #[serde(default = "default_limit")]
    pub limit: usize,
    pub max_id: Option<String>,
    pub min_id: Option<String>,
    pub since_id: Option<String>,
}

const fn default_limit() -> usize {
    20
}
