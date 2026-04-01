mod common;

use axum::http::StatusCode;
use sqlx::PgPool;

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
async fn health_check(pool: PgPool) {
    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get("/fediway/health").await;
    assert_eq!(resp.status, StatusCode::OK);
}
