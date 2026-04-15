mod common;

use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

use axum::Router;
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
use axum::routing::get;
use sqlx::PgPool;

use server::auth::BearerToken;
use server::mastodon::resolve::{ResolveError, Resolver};

fn test_post(url: &str, handle: &str, content: &str) -> serde_json::Value {
    serde_json::json!({
        "url": url,
        "content": format!("<p>{content}</p>"),
        "text": content,
        "author": {
            "handle": handle,
            "display_name": handle.trim_start_matches('@').split('@').next().unwrap(),
            "url": format!("https://example.com/@{}", handle.trim_start_matches('@').split('@').next().unwrap()),
            "emojis": []
        },
        "published_at": "2026-03-01T12:00:00Z",
        "sensitive": false,
        "media": [],
        "engagement": { "replies": 0, "reposts": 0, "likes": 0 },
        "tags": [],
        "emojis": []
    })
}

async fn seed_cached_status(pool: &PgPool, post_uri: &str) -> i64 {
    common::setup_db(pool).await;
    let post = test_post(post_uri, "@a@example.com", "hello");
    state::statuses::map_post(pool, "test.provider", 1, post_uri, post_uri, &post)
        .await
        .expect("map_post failed")
}

fn http_client() -> reqwest::Client {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .connect_timeout(Duration::from_secs(2))
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .unwrap()
}

async fn serve(router: Router) -> String {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, router).await.unwrap();
    });
    format!("http://127.0.0.1:{port}")
}

fn ok_with_status_id(id: &str) -> axum::response::Response {
    axum::Json(serde_json::json!({
        "accounts": [],
        "hashtags": [],
        "statuses": [{ "id": id }]
    }))
    .into_response()
}

fn ok_empty() -> axum::response::Response {
    axum::Json(serde_json::json!({
        "accounts": [],
        "hashtags": [],
        "statuses": []
    }))
    .into_response()
}

#[sqlx::test]
async fn resolve_returns_cached_mapping_without_http(pool: PgPool) {
    let snowflake = seed_cached_status(&pool, "https://example.com/1").await;
    state::statuses::set_mastodon_local_id(&pool, snowflake, 12345)
        .await
        .unwrap();

    let calls = Arc::new(AtomicUsize::new(0));
    let calls_clone = calls.clone();
    let router = Router::new().route(
        "/api/v2/search",
        get(move || {
            let calls = calls_clone.clone();
            async move {
                calls.fetch_add(1, Ordering::SeqCst);
                ok_with_status_id("99")
            }
        }),
    );
    let base = serve(router).await;

    let resolver = Resolver::new(pool, http_client(), Some(base));
    let result = resolver
        .resolve(snowflake, &BearerToken::new("tok".into()))
        .await
        .unwrap();

    assert_eq!(result, 12345);
    assert_eq!(calls.load(Ordering::SeqCst), 0);
}

#[sqlx::test]
async fn resolve_fetches_and_persists_on_first_call(pool: PgPool) {
    let snowflake = seed_cached_status(&pool, "https://example.com/1").await;

    let received_token = Arc::new(tokio::sync::Mutex::new(None::<String>));
    let received_clone = received_token.clone();
    let router = Router::new().route(
        "/api/v2/search",
        get(move |headers: HeaderMap| {
            let received = received_clone.clone();
            async move {
                *received.lock().await = headers
                    .get("authorization")
                    .and_then(|v| v.to_str().ok())
                    .map(String::from);
                ok_with_status_id("54321")
            }
        }),
    );
    let base = serve(router).await;

    let resolver = Resolver::new(pool.clone(), http_client(), Some(base));
    let result = resolver
        .resolve(snowflake, &BearerToken::new("user_token".into()))
        .await
        .unwrap();

    assert_eq!(result, 54321);
    assert_eq!(
        received_token.lock().await.as_deref(),
        Some("Bearer user_token")
    );

    let row = state::statuses::find_by_id(&pool, snowflake)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(row.mastodon_local_id, Some(54321));
}

#[sqlx::test]
async fn resolve_missing_snowflake_returns_not_found(pool: PgPool) {
    common::setup_db(&pool).await;
    let resolver = Resolver::new(pool, http_client(), Some("http://unused".into()));
    let err = resolver
        .resolve(999, &BearerToken::new("tok".into()))
        .await
        .unwrap_err();
    assert_eq!(err, ResolveError::NotFound);
}

#[sqlx::test]
async fn resolve_empty_statuses_is_unresolvable(pool: PgPool) {
    let snowflake = seed_cached_status(&pool, "https://example.com/private").await;
    let router = Router::new().route("/api/v2/search", get(|| async { ok_empty() }));
    let base = serve(router).await;

    let resolver = Resolver::new(pool, http_client(), Some(base));
    let err = resolver
        .resolve(snowflake, &BearerToken::new("tok".into()))
        .await
        .unwrap_err();
    assert_eq!(err, ResolveError::Unresolvable);
}

#[sqlx::test]
async fn resolve_401_is_forbidden(pool: PgPool) {
    let snowflake = seed_cached_status(&pool, "https://example.com/scope").await;
    let router = Router::new().route(
        "/api/v2/search",
        get(|| async { (StatusCode::UNAUTHORIZED, "no scope").into_response() }),
    );
    let base = serve(router).await;

    let resolver = Resolver::new(pool, http_client(), Some(base));
    let err = resolver
        .resolve(snowflake, &BearerToken::new("tok".into()))
        .await
        .unwrap_err();
    assert_eq!(err, ResolveError::Forbidden);
}

#[sqlx::test]
async fn resolve_422_is_blocked(pool: PgPool) {
    let snowflake = seed_cached_status(&pool, "https://blocked.example/1").await;
    let router = Router::new().route(
        "/api/v2/search",
        get(|| async { (StatusCode::UNPROCESSABLE_ENTITY, "blocked").into_response() }),
    );
    let base = serve(router).await;

    let resolver = Resolver::new(pool, http_client(), Some(base));
    let err = resolver
        .resolve(snowflake, &BearerToken::new("tok".into()))
        .await
        .unwrap_err();
    assert_eq!(err, ResolveError::Blocked);
}

#[sqlx::test]
async fn resolve_429_propagates_retry_after(pool: PgPool) {
    let snowflake = seed_cached_status(&pool, "https://example.com/rl").await;
    let router = Router::new().route(
        "/api/v2/search",
        get(|| async {
            let mut headers = HeaderMap::new();
            headers.insert("retry-after", "42".parse().unwrap());
            (StatusCode::TOO_MANY_REQUESTS, headers, "slow down").into_response()
        }),
    );
    let base = serve(router).await;

    let resolver = Resolver::new(pool, http_client(), Some(base));
    let err = resolver
        .resolve(snowflake, &BearerToken::new("tok".into()))
        .await
        .unwrap_err();
    assert_eq!(
        err,
        ResolveError::RateLimited {
            retry_after: Some(Duration::from_secs(42))
        }
    );
}

#[sqlx::test]
async fn resolve_unreachable_mastodon_returns_unreachable(pool: PgPool) {
    let snowflake = seed_cached_status(&pool, "https://example.com/1").await;

    let resolver = Resolver::new(pool, http_client(), Some("http://127.0.0.1:1".into()));
    let err = resolver
        .resolve(snowflake, &BearerToken::new("tok".into()))
        .await
        .unwrap_err();
    assert_eq!(err, ResolveError::Unreachable);
}

#[sqlx::test]
async fn resolve_coalesces_concurrent_callers(pool: PgPool) {
    let snowflake = seed_cached_status(&pool, "https://example.com/concurrent").await;

    let call_count = Arc::new(AtomicUsize::new(0));
    let counter = call_count.clone();
    let router = Router::new().route(
        "/api/v2/search",
        get(move || {
            let counter = counter.clone();
            async move {
                counter.fetch_add(1, Ordering::SeqCst);
                tokio::time::sleep(Duration::from_millis(150)).await;
                ok_with_status_id("7777")
            }
        }),
    );
    let base = serve(router).await;

    let resolver = Resolver::new(pool, http_client(), Some(base));

    let mut handles = Vec::new();
    for _ in 0..10 {
        let r = resolver.clone();
        handles.push(tokio::spawn(async move {
            r.resolve(snowflake, &BearerToken::new("tok".into())).await
        }));
    }

    for h in handles {
        let result = h.await.unwrap().unwrap();
        assert_eq!(result, 7777);
    }

    assert_eq!(
        call_count.load(Ordering::SeqCst),
        1,
        "single-flight must collapse concurrent resolves to one upstream call"
    );
}
