use std::borrow::Cow;
use std::time::Instant;

use axum::Json;
use axum::http::HeaderMap;
use common::types::Post;
use feed::Feed;
use mastodon::Status;
use serde::Deserialize;
use sources::mastodon::CachedPost;

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

    /// The authenticated viewer's Mastodon `accounts.id`, or `None` for
    /// anonymous requests. Threaded all the way to `fetch_by_ids` so every
    /// status in the response carries correct `favourited`/`bookmarked`/
    /// `reblogged` state instead of hardcoded `false`.
    fn viewer_id(&self) -> Option<i64>;

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
            let cached: Vec<CachedPost> = candidates
                .into_iter()
                .map(|c| CachedPost::from_post(c.item, &state.instance_domain))
                .collect();
            let built = statuses::hydrate(
                &state.pool,
                &state.instance_domain,
                &state.media,
                cached,
                self.viewer_id(),
            )
            .await;
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
