mod common;

use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

use axum::Router;
use axum::body::Body;
use axum::http::{Request, StatusCode};
use axum::routing::post;
use http_body_util::BodyExt;
use sources::mastodon::MediaConfig;
use sqlx::PgPool;
use state::cache::Cache;
use state::feed_store::FeedStore;
use tower::ServiceExt;

use server::middleware::mastodon_fallback;
use server::state::{AppState, AppStateInner};

async fn test_state(pool: PgPool, mastodon_api_url: String) -> AppState {
    common::setup_db(&pool).await;
    let feed_store = FeedStore::new(Cache::disabled(), Duration::from_secs(60));
    let media = MediaConfig::new("example.com".into(), false);
    AppStateInner::new(
        pool,
        feed_store,
        media,
        "nomic_v1.5_64d".into(),
        "example.com".into(),
        Some(mastodon_api_url),
    )
}

async fn start_mock_mastodon(calls: Arc<AtomicUsize>) -> String {
    let router = Router::new().fallback(move || {
        let calls = calls.clone();
        async move {
            calls.fetch_add(1, Ordering::SeqCst);
            StatusCode::OK
        }
    });
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, router).await.unwrap();
    });
    format!("http://127.0.0.1:{port}")
}

#[sqlx::test]
async fn post_handler_200_response_bypasses_proxy(pool: PgPool) {
    let calls = Arc::new(AtomicUsize::new(0));
    let mastodon_url = start_mock_mastodon(calls.clone()).await;
    let state = test_state(pool, mastodon_url).await;

    let router = Router::new()
        .route(
            "/test/registered",
            post(|| async { (StatusCode::OK, "inner handler ran") }),
        )
        .route_layer(axum::middleware::from_fn_with_state(
            state,
            mastodon_fallback::fallback,
        ));

    let req = Request::post("/test/registered")
        .body(Body::from("client body"))
        .unwrap();
    let resp = router.oneshot(req).await.unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = resp.into_body().collect().await.unwrap().to_bytes();
    assert_eq!(&body[..], b"inner handler ran");
    assert_eq!(calls.load(Ordering::SeqCst), 0);
}

#[sqlx::test]
async fn post_handler_404_response_falls_through_with_body(pool: PgPool) {
    let received_body = Arc::new(tokio::sync::Mutex::new(None::<String>));
    let received_clone = received_body.clone();

    let mock = Router::new().route(
        "/test/proxied",
        post(move |body: String| {
            let received = received_clone.clone();
            async move {
                *received.lock().await = Some(body);
                StatusCode::OK
            }
        }),
    );
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, mock).await.unwrap();
    });
    let state = test_state(pool, format!("http://127.0.0.1:{port}")).await;

    let router = Router::new()
        .route("/test/proxied", post(|| async { StatusCode::NOT_FOUND }))
        .route_layer(axum::middleware::from_fn_with_state(
            state,
            mastodon_fallback::fallback,
        ));

    let req = Request::post("/test/proxied")
        .header("content-type", "application/json")
        .body(Body::from(r#"{"status":"hello"}"#))
        .unwrap();
    let resp = router.oneshot(req).await.unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let forwarded = received_body.lock().await;
    assert_eq!(forwarded.as_deref(), Some(r#"{"status":"hello"}"#));
}

#[sqlx::test]
async fn method_not_allowed_falls_through_to_proxy(pool: PgPool) {
    let calls = Arc::new(AtomicUsize::new(0));
    let mastodon_url = start_mock_mastodon(calls.clone()).await;
    let state = test_state(pool, mastodon_url).await;

    let router = Router::new()
        .route(
            "/test/get_only",
            axum::routing::get(|| async { StatusCode::OK }),
        )
        .route_layer(axum::middleware::from_fn_with_state(
            state,
            mastodon_fallback::fallback,
        ));

    let req = Request::post("/test/get_only")
        .body(Body::from("body"))
        .unwrap();
    let resp = router.oneshot(req).await.unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    assert_eq!(calls.load(Ordering::SeqCst), 1);
}
