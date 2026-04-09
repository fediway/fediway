mod statuses;
mod suggestions;
mod timelines;
mod trends;

use axum::Router;
use axum::routing::get;

use crate::middleware::mastodon_fallback;
use crate::state::AppState;

pub fn router(state: AppState) -> Router<AppState> {
    let with_fallback = Router::new()
        .route("/api/v1/statuses/{id}", get(statuses::detail))
        .route("/api/v1/statuses/{id}/context", get(statuses::context))
        .route_layer(axum::middleware::from_fn_with_state(
            state,
            mastodon_fallback::fallback,
        ));

    Router::new()
        .route("/api/v1/timelines/home", get(timelines::home))
        .route("/api/v1/timelines/tag/{hashtag}", get(timelines::tag))
        .route("/api/v1/timelines/link", get(timelines::link))
        .route("/api/v1/trends/statuses", get(trends::statuses))
        .route("/api/v1/trends/tags", get(trends::tags))
        .route("/api/v1/trends/links", get(trends::links))
        .route("/api/v2/suggestions", get(suggestions::handle))
        .merge(with_fallback)
}
