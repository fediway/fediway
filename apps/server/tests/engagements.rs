mod common;

use std::sync::Arc;

use axum::Router;
use axum::body::Body;
use axum::extract::Path;
use axum::http::{HeaderMap, Request, StatusCode};
use axum::response::IntoResponse;
use axum::routing::{get, post};
use serde_json::json;
use sqlx::PgPool;
use tokio::sync::Mutex;

fn sample_post(url: &str, handle: &str) -> serde_json::Value {
    json!({
        "url": url,
        "content": "<p>hello</p>",
        "text": "hello",
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

async fn seed_with_mapping(
    pool: &PgPool,
    post_uri: &str,
    provider: &str,
    remote_id: i64,
    mastodon_id: i64,
) -> i64 {
    let post = sample_post(post_uri, "@a@example.com");
    let snowflake = state::statuses::map_post(pool, provider, remote_id, post_uri, post_uri, &post)
        .await
        .unwrap();
    state::statuses::set_mastodon_local_id(pool, snowflake, mastodon_id)
        .await
        .unwrap();
    snowflake
}

async fn serve(router: Router) -> String {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, router).await.unwrap();
    });
    format!("http://127.0.0.1:{port}")
}

#[sqlx::test]
async fn favourite_end_to_end_rewrites_response_id(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().insert(&pool).await;

    let received_id = Arc::new(Mutex::new(None::<String>));
    let received_clone = received_id.clone();
    let router = Router::new().route(
        "/api/v1/statuses/{id}/favourite",
        post(move |Path(id): Path<String>| {
            let received = received_clone.clone();
            async move {
                *received.lock().await = Some(id.clone());
                axum::Json(json!({
                    "id": id,
                    "favourited": true,
                    "reblogged": false
                }))
            }
        }),
    );
    let base = serve(router).await;

    let app = common::TestApp::from_pool_with_mastodon(pool.clone(), Some(base)).await;
    let snowflake = seed_with_mapping(&pool, "https://example.com/1", "p", 1, 42).await;

    let req = Request::post(format!("/api/v1/statuses/{snowflake}/favourite"))
        .header("authorization", format!("Bearer {}", user.token))
        .body(Body::empty())
        .unwrap();
    let resp = app.raw_request(req).await;

    assert_eq!(resp.status, StatusCode::OK);
    let json = resp.json();
    assert_eq!(json["id"], snowflake.to_string());
    assert_eq!(json["favourited"], true);
    assert_eq!(received_id.lock().await.as_deref(), Some("42"));
}

#[sqlx::test]
async fn favourite_without_auth_returns_401(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let app =
        common::TestApp::from_pool_with_mastodon(pool, Some("http://127.0.0.1:1".into())).await;

    let req = Request::post("/api/v1/statuses/12345/favourite")
        .body(Body::empty())
        .unwrap();
    let resp = app.raw_request(req).await;

    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn favourite_native_mastodon_id_passes_through(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().insert(&pool).await;

    let received_id = Arc::new(Mutex::new(None::<String>));
    let received_clone = received_id.clone();
    let router = Router::new().route(
        "/api/v1/statuses/{id}/favourite",
        post(move |Path(id): Path<String>| {
            let received = received_clone.clone();
            async move {
                *received.lock().await = Some(id.clone());
                axum::Json(json!({ "id": id, "favourited": true }))
            }
        }),
    );
    let base = serve(router).await;

    let app = common::TestApp::from_pool_with_mastodon(pool, Some(base)).await;

    let req = Request::post("/api/v1/statuses/99999999/favourite")
        .header("authorization", format!("Bearer {}", user.token))
        .body(Body::empty())
        .unwrap();
    let resp = app.raw_request(req).await;

    assert_eq!(resp.status, StatusCode::OK);
    assert_eq!(received_id.lock().await.as_deref(), Some("99999999"));
}

#[sqlx::test]
async fn reply_translates_in_reply_to_id_in_body(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().insert(&pool).await;

    let received_body = Arc::new(Mutex::new(None::<serde_json::Value>));
    let received_clone = received_body.clone();
    let router = Router::new().route(
        "/api/v1/statuses",
        post(move |body: String| {
            let received = received_clone.clone();
            async move {
                let parsed: serde_json::Value = serde_json::from_str(&body).unwrap();
                *received.lock().await = Some(parsed);
                axum::Json(json!({ "id": "9999", "content": "<p>reply</p>" }))
            }
        }),
    );
    let base = serve(router).await;

    let app = common::TestApp::from_pool_with_mastodon(pool.clone(), Some(base)).await;
    let parent_snowflake =
        seed_with_mapping(&pool, "https://example.com/parent", "p", 1, 555).await;

    let req = Request::post("/api/v1/statuses")
        .header("authorization", format!("Bearer {}", user.token))
        .header("content-type", "application/json")
        .body(Body::from(
            json!({
                "status": "hello",
                "in_reply_to_id": parent_snowflake.to_string()
            })
            .to_string(),
        ))
        .unwrap();
    let resp = app.raw_request(req).await;

    assert_eq!(resp.status, StatusCode::OK);
    let forwarded = received_body.lock().await;
    let body = forwarded.as_ref().unwrap();
    assert_eq!(body["status"], "hello");
    assert_eq!(body["in_reply_to_id"], "555");
}

#[sqlx::test]
async fn report_translates_status_ids_array(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().insert(&pool).await;

    let received_body = Arc::new(Mutex::new(None::<serde_json::Value>));
    let received_clone = received_body.clone();
    let router = Router::new().route(
        "/api/v1/reports",
        post(move |body: String| {
            let received = received_clone.clone();
            async move {
                let parsed: serde_json::Value = serde_json::from_str(&body).unwrap();
                *received.lock().await = Some(parsed);
                axum::Json(json!({
                    "id": "1",
                    "status_ids": ["100", "200"],
                    "account_id": "5"
                }))
            }
        }),
    );
    let base = serve(router).await;

    let app = common::TestApp::from_pool_with_mastodon(pool.clone(), Some(base)).await;
    let snow_a = seed_with_mapping(&pool, "https://example.com/a", "p", 1, 100).await;
    let snow_b = seed_with_mapping(&pool, "https://example.com/b", "p", 2, 200).await;

    let req = Request::post("/api/v1/reports")
        .header("authorization", format!("Bearer {}", user.token))
        .header("content-type", "application/json")
        .body(Body::from(
            json!({
                "account_id": "5",
                "status_ids": [snow_a.to_string(), snow_b.to_string()],
                "comment": "spam"
            })
            .to_string(),
        ))
        .unwrap();
    let resp = app.raw_request(req).await;

    assert_eq!(resp.status, StatusCode::OK);

    let forwarded = received_body.lock().await;
    let body = forwarded.as_ref().unwrap();
    let forwarded_ids = body["status_ids"].as_array().unwrap();
    assert_eq!(forwarded_ids[0], "100");
    assert_eq!(forwarded_ids[1], "200");

    let response_ids = resp.json()["status_ids"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap().to_string())
        .collect::<Vec<_>>();
    assert!(response_ids.contains(&snow_a.to_string()));
    assert!(response_ids.contains(&snow_b.to_string()));
}

#[sqlx::test]
async fn detail_post_resolve_proxies_to_mastodon(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;

    let router = Router::new().route(
        "/api/v1/statuses/{id}",
        get(|Path(id): Path<String>, _: HeaderMap| async move {
            axum::Json(json!({
                "id": id,
                "content": "<p>fresh from mastodon</p>",
                "favourites_count": 99
            }))
            .into_response()
        }),
    );
    let base = serve(router).await;

    let app = common::TestApp::from_pool_with_mastodon(pool.clone(), Some(base)).await;
    let snowflake = seed_with_mapping(&pool, "https://example.com/1", "p", 1, 4242).await;

    let resp = app.get(&format!("/api/v1/statuses/{snowflake}")).await;

    assert_eq!(resp.status, StatusCode::OK);
    let json = resp.json();
    assert_eq!(json["id"], snowflake.to_string());
    assert_eq!(json["content"], "<p>fresh from mastodon</p>");
    assert_eq!(json["favourites_count"], 99);
}
