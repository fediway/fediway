mod common;

use axum::http::StatusCode;

#[tokio::test]
async fn health_check() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    let resp = app.get("/fediway/health").await;
    assert_eq!(resp.status, StatusCode::OK);
}
