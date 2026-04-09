// TODO: Add tower HTTP metrics middleware (fediway_http_requests_total, fediway_http_request_duration_seconds)
// See todo/prometheus/fediway.md for the full spec.

mod commonfeed;
mod fediway;
mod mastodon;

use axum::Router;
use axum::http::Method;
use axum::http::header::{ACCEPT, ACCEPT_LANGUAGE, AUTHORIZATION, CONTENT_TYPE};
// TODO: Add rate limiting via tower_governor once axum ConnectInfo is
// configured (required for per-IP limiting with tower::ServiceExt::oneshot tests).
use tower_http::cors::{AllowOrigin, CorsLayer, ExposeHeaders};

use crate::state::AppState;

/// Build the application router.
///
/// CORS follows Mastodon's policy: `Access-Control-Allow-Origin: *` on all
/// API endpoints. Third-party web clients (Elk, Phanpy, etc.) rely on this
/// to make cross-origin requests. Authentication is handled by OAuth tokens,
/// not CORS origin restrictions.
pub fn router(state: AppState) -> Router {
    Router::new()
        .merge(commonfeed::router())
        .merge(fediway::router())
        .merge(mastodon::router(state.clone()))
        .layer(
            CorsLayer::new()
                .allow_origin(AllowOrigin::any())
                .allow_methods([
                    Method::GET,
                    Method::POST,
                    Method::PUT,
                    Method::DELETE,
                    Method::PATCH,
                    Method::OPTIONS,
                ])
                .allow_headers([AUTHORIZATION, ACCEPT, ACCEPT_LANGUAGE, CONTENT_TYPE])
                .expose_headers(ExposeHeaders::list([
                    "Link".parse().unwrap(),
                    "X-RateLimit-Limit".parse().unwrap(),
                    "X-RateLimit-Remaining".parse().unwrap(),
                    "X-RateLimit-Reset".parse().unwrap(),
                    "X-Request-Id".parse().unwrap(),
                ])),
        )
        .with_state(state)
}
