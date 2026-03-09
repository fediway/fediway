mod commonfeed;
mod fediway;
mod mastodon;

use axum::Router;
use axum::http::Method;
use axum::http::header::{ACCEPT, ACCEPT_LANGUAGE, AUTHORIZATION, CONTENT_TYPE};
use sqlx::PgPool;
use tower_http::cors::{AllowOrigin, CorsLayer};

pub fn router(db: PgPool, instance_domain: &str) -> Router {
    let allow_origin = if instance_domain.is_empty() {
        tracing::warn!("INSTANCE_DOMAIN is empty, allowing all CORS origins");
        AllowOrigin::any()
    } else {
        let origin = format!("https://{instance_domain}");
        match origin.parse() {
            Ok(value) => AllowOrigin::exact(value),
            Err(err) => {
                tracing::warn!(domain = %instance_domain, error = %err, "invalid CORS origin, allowing all origins");
                AllowOrigin::any()
            }
        }
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
        .with_state(db)
}
