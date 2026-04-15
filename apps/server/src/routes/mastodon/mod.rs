mod create_report;
mod create_status;
mod engagements;
mod error;
mod extract;
mod statuses;
mod suggestions;
mod timelines;
mod trends;

use axum::Router;
use axum::routing::{get, post};

use crate::middleware::mastodon_fallback;
use crate::state::AppState;

pub fn router(state: AppState) -> Router<AppState> {
    let pf = statuses::proxy_fallback;
    let with_fallback = Router::new()
        .route("/api/v1/statuses", post(create_status::handle))
        .route("/api/v1/reports", post(create_report::handle))
        .route(
            "/api/v1/statuses/{id}",
            get(statuses::detail).delete(pf).put(pf),
        )
        .route("/api/v1/statuses/{id}/context", get(statuses::context))
        .route(
            "/api/v1/statuses/{id}/favourite",
            post(engagements::favourite),
        )
        .route(
            "/api/v1/statuses/{id}/unfavourite",
            post(engagements::unfavourite),
        )
        .route("/api/v1/statuses/{id}/reblog", post(engagements::reblog))
        .route(
            "/api/v1/statuses/{id}/unreblog",
            post(engagements::unreblog),
        )
        .route(
            "/api/v1/statuses/{id}/bookmark",
            post(engagements::bookmark),
        )
        .route(
            "/api/v1/statuses/{id}/unbookmark",
            post(engagements::unbookmark),
        )
        .route("/api/v1/statuses/{id}/{action}", post(pf).get(pf))
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
