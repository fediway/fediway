mod callback;
mod verify;

use axum::Router;
use axum::routing::{get, post};
use sqlx::PgPool;

pub fn router() -> Router<PgPool> {
    Router::new()
        .route("/.well-known/commonfeed/{token}", get(verify::handle))
        .route("/commonfeed/callback", post(callback::handle))
}
