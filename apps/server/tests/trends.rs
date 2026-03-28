mod common;

use axum::http::StatusCode;

#[tokio::test]
async fn trending_statuses_empty_returns_ok() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    let resp = app.get("/api/v1/trends/statuses").await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    assert!(
        json.is_array(),
        "Mastodon trends/statuses must return array"
    );
}

#[tokio::test]
async fn trending_tags_empty_returns_ok() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    let resp = app.get("/api/v1/trends/tags").await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    assert!(json.is_array(), "Mastodon trends/tags must return array");
}

#[tokio::test]
async fn trending_links_empty_returns_ok() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    let resp = app.get("/api/v1/trends/links").await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    assert!(json.is_array(), "Mastodon trends/links must return array");
}

#[tokio::test]
async fn unknown_route_returns_404() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    let resp = app.get("/api/v1/nonexistent").await;
    assert_eq!(resp.status, StatusCode::NOT_FOUND);
}
