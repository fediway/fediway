mod home;
mod suggestions;
mod timelines;
mod trends;

use axum::Router;
use axum::routing::get;
use sqlx::PgPool;

pub fn router() -> Router<PgPool> {
    Router::new()
        .route("/api/v1/timelines/home", get(home::handle))
        .route("/api/v1/timelines/tag/{hashtag}", get(timelines::tag))
        .route("/api/v1/trends/statuses", get(trends::statuses))
        .route("/api/v1/trends/tags", get(trends::tags))
        .route("/api/v2/suggestions", get(suggestions::handle))
}
