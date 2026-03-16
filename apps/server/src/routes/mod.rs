mod commonfeed;
mod fediway;
mod mastodon;

use axum::Router;
use axum::http::Method;
use axum::http::header::{ACCEPT, ACCEPT_LANGUAGE, AUTHORIZATION, CONTENT_TYPE};
use tower_http::cors::{AllowOrigin, CorsLayer};

use crate::state::AppState;

pub fn router(state: AppState, instance_domain: &str) -> Router {
    let allow_origin = if instance_domain.is_empty() {
        tracing::warn!("INSTANCE_DOMAIN is empty, allowing all CORS origins (dev mode)");
        AllowOrigin::any()
    } else {
        let origin = format!("https://{instance_domain}");
        AllowOrigin::exact(
            origin
                .parse()
                .unwrap_or_else(|e| panic!("invalid INSTANCE_DOMAIN '{instance_domain}': {e}")),
        )
    };

    Router::new()
        .merge(commonfeed::router())
        .merge(fediway::router())
        .merge(mastodon::router())
        .layer(
            CorsLayer::new()
                .allow_origin(allow_origin)
                .allow_methods([Method::GET, Method::POST])
                .allow_headers([AUTHORIZATION, ACCEPT, ACCEPT_LANGUAGE, CONTENT_TYPE]),
        )
        .with_state(state)
}
