mod commonfeed;
mod fediway;
mod mastodon;

use std::sync::Arc;

use axum::Router;
use axum::http::Method;
use axum::http::header::{ACCEPT, ACCEPT_LANGUAGE, AUTHORIZATION, CONTENT_TYPE};
use sqlx::PgPool;
use tower_governor::GovernorLayer;
use tower_governor::governor::GovernorConfigBuilder;
use tower_http::cors::{AllowOrigin, CorsLayer};

pub fn router(db: PgPool, instance_domain: &str) -> Router {
    let governor = GovernorConfigBuilder::default()
        .per_second(1)
        .burst_size(300)
        .finish()
        .expect("invalid rate limit config");

    let origin = format!("https://{instance_domain}");

    Router::new()
        .merge(commonfeed::router())
        .merge(fediway::router())
        .merge(mastodon::router())
        .layer(
            CorsLayer::new()
                .allow_origin(AllowOrigin::exact(origin.parse().expect("invalid origin")))
                .allow_methods([Method::GET, Method::POST])
                .allow_headers([AUTHORIZATION, ACCEPT, ACCEPT_LANGUAGE, CONTENT_TYPE]),
        )
        .layer(GovernorLayer {
            config: Arc::new(governor),
        })
        .with_state(db)
}
