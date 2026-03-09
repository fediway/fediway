mod health;

use axum::Router;
use axum::routing::get;
use sqlx::PgPool;

pub fn router() -> Router<PgPool> {
    Router::new().route("/fediway/health", get(health::handle))
}
