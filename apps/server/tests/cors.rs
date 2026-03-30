mod common;

use axum::http::StatusCode;

#[tokio::test]
async fn cors_allows_any_origin() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    // Simulate a request from a third-party web client (e.g., Elk)
    let response = app
        .raw_request(
            axum::http::Request::get("/fediway/health")
                .header("origin", "https://elk.zone")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await;

    assert_eq!(response.status, StatusCode::OK);
    assert_eq!(
        response.header("access-control-allow-origin"),
        Some("*"),
        "must allow any origin (Mastodon compatibility)"
    );
}

#[tokio::test]
async fn cors_preflight_allows_methods() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    let response = app
        .raw_request(
            axum::http::Request::builder()
                .method("OPTIONS")
                .uri("/api/v1/trends/statuses")
                .header("origin", "https://phanpy.social")
                .header("access-control-request-method", "GET")
                .header("access-control-request-headers", "authorization")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await;

    // Preflight should succeed
    assert_eq!(response.status, StatusCode::OK);
    assert_eq!(response.header("access-control-allow-origin"), Some("*"),);

    let allowed_methods = response
        .header("access-control-allow-methods")
        .unwrap_or("");
    assert!(
        allowed_methods.contains("GET"),
        "must allow GET, got: {allowed_methods}"
    );
}

#[tokio::test]
async fn cors_exposes_rate_limit_headers() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    let response = app
        .raw_request(
            axum::http::Request::get("/fediway/health")
                .header("origin", "https://elk.zone")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await;

    let exposed = response
        .header("access-control-expose-headers")
        .unwrap_or("");

    assert!(
        exposed.contains("x-request-id") || exposed.contains("X-Request-Id"),
        "must expose X-Request-Id header, got: {exposed}"
    );
}
