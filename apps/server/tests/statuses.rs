mod common;

use axum::http::StatusCode;
use axum::routing::get;
use sqlx::PgPool;

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

fn test_post_with_reply(
    url: &str,
    handle: &str,
    content: &str,
    reply_to: serde_json::Value,
) -> serde_json::Value {
    let mut post = test_post(url, handle, content);
    post["reply_to"] = reply_to;
    post
}

async fn map(pool: &PgPool, domain: &str, remote_id: i64, post: &serde_json::Value) -> i64 {
    common::setup_db(pool).await;
    let url = post["url"].as_str().unwrap();
    state::statuses::map_post(pool, domain, remote_id, url, url, post)
        .await
        .expect("map_post failed")
}

// --- Error cases ---

#[sqlx::test]
async fn detail_unknown_id_returns_404(pool: PgPool) {
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get("/api/v1/statuses/999999999999999999").await;
    assert_eq!(resp.status, StatusCode::NOT_FOUND);
}

#[sqlx::test]
async fn detail_non_numeric_id_returns_404(pool: PgPool) {
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get("/api/v1/statuses/not-a-number").await;
    assert_eq!(resp.status, StatusCode::NOT_FOUND);
}

#[sqlx::test]
async fn context_unknown_id_returns_404(pool: PgPool) {
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get("/api/v1/statuses/999999999999999999/context").await;
    assert_eq!(resp.status, StatusCode::NOT_FOUND);
}

// --- Detail happy path ---

#[sqlx::test]
async fn detail_returns_cached_post(pool: PgPool) {
    let post = test_post(
        "https://mastodon.social/@alice/123",
        "@alice@mastodon.social",
        "Hello world",
    );
    let id = map(&pool, "test.provider", 42, &post).await;

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get(&format!("/api/v1/statuses/{id}")).await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    assert_eq!(json["id"], id.to_string());
    assert!(json["content"].as_str().unwrap().contains("Hello world"));
    assert_eq!(json["account"]["username"], "alice");
    assert_eq!(json["url"], "https://mastodon.social/@alice/123");
}

#[sqlx::test]
async fn detail_same_post_returns_same_id(pool: PgPool) {
    let post = test_post("https://example.com/post/1", "@test@example.com", "test");

    let id1 = map(&pool, "test.provider", 99, &post).await;
    let id2 = map(&pool, "test.provider", 99, &post).await;

    assert_eq!(
        id1, id2,
        "same provider + remote_id must return same snowflake"
    );
}

#[sqlx::test]
async fn detail_updates_cache_on_remap(pool: PgPool) {
    let post_v1 = test_post(
        "https://example.com/post/1",
        "@alice@example.com",
        "version 1",
    );
    let id = map(&pool, "test.provider", 50, &post_v1).await;

    let post_v2 = test_post(
        "https://example.com/post/1",
        "@alice@example.com",
        "version 2",
    );
    let id2 = map(&pool, "test.provider", 50, &post_v2).await;
    assert_eq!(id, id2);

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get(&format!("/api/v1/statuses/{id}")).await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    assert!(
        json["content"].as_str().unwrap().contains("version 2"),
        "cache should reflect latest data"
    );
}

// --- Context: ancestors ---

#[sqlx::test]
async fn context_returns_empty_arrays_for_post_without_thread(pool: PgPool) {
    let post = test_post(
        "https://example.com/post/1",
        "@test@example.com",
        "standalone",
    );
    let id = map(&pool, "nonexistent.provider", 1, &post).await;

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get(&format!("/api/v1/statuses/{id}/context")).await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    assert!(json["ancestors"].as_array().unwrap().is_empty());
    assert!(json["descendants"].as_array().unwrap().is_empty());
}

#[sqlx::test]
async fn context_builds_ancestors_from_reply_chain(pool: PgPool) {
    let grandparent = test_post(
        "https://example.com/post/gp",
        "@alice@example.com",
        "grandparent",
    );
    let parent = test_post_with_reply(
        "https://example.com/post/p",
        "@bob@example.com",
        "parent",
        grandparent.clone(),
    );
    let child = test_post_with_reply(
        "https://example.com/post/c",
        "@carol@example.com",
        "child",
        parent.clone(),
    );

    let id = map(&pool, "test.provider", 3, &child).await;

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get(&format!("/api/v1/statuses/{id}/context")).await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    let ancestors = json["ancestors"].as_array().unwrap();
    assert_eq!(ancestors.len(), 2);
    assert!(
        ancestors[0]["content"]
            .as_str()
            .unwrap()
            .contains("grandparent"),
        "oldest ancestor first"
    );
    assert!(
        ancestors[1]["content"].as_str().unwrap().contains("parent"),
        "direct parent second"
    );
}

#[sqlx::test]
async fn context_ancestors_get_snowflake_ids(pool: PgPool) {
    let parent = test_post("https://example.com/post/p", "@alice@example.com", "parent");
    let mut parent_with_ids = parent.clone();
    parent_with_ids["provider_id"] = serde_json::json!(10);
    parent_with_ids["provider_domain"] = serde_json::json!("test.provider");

    let child = test_post_with_reply(
        "https://example.com/post/c",
        "@bob@example.com",
        "child",
        parent_with_ids,
    );
    let child_id = map(&pool, "test.provider", 11, &child).await;

    let app = common::TestApp::from_pool(pool).await;
    let resp = app
        .get(&format!("/api/v1/statuses/{child_id}/context"))
        .await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    let ancestors = json["ancestors"].as_array().unwrap();
    assert_eq!(ancestors.len(), 1);

    let ancestor_id = ancestors[0]["id"].as_str().unwrap();
    assert!(
        ancestor_id.parse::<i64>().is_ok(),
        "ancestor should have numeric snowflake ID, got: {ancestor_id}"
    );
}

// --- Batch mapping ---

#[sqlx::test]
async fn batch_map_posts_returns_consistent_ids(pool: PgPool) {
    common::setup_db(&pool).await;
    use state::statuses::{PostMapping, map_posts};

    let data1 = test_post("https://example.com/1", "@a@example.com", "one");
    let data2 = test_post("https://example.com/2", "@b@example.com", "two");

    let mappings = vec![
        PostMapping {
            provider_domain: "test.provider",
            remote_id: 1,
            post_url: "https://example.com/1",
            post_uri: "https://example.com/1",
            post_data: &data1,
        },
        PostMapping {
            provider_domain: "test.provider",
            remote_id: 2,
            post_url: "https://example.com/2",
            post_uri: "https://example.com/2",
            post_data: &data2,
        },
    ];

    let result = map_posts(&pool, &mappings).await.unwrap();
    assert_eq!(result.len(), 2);

    let id1 = result[&("test.provider".into(), 1)];
    let id2 = result[&("test.provider".into(), 2)];
    assert_ne!(id1, id2, "different posts get different IDs");

    // Re-map same posts, verify same IDs
    let result2 = map_posts(&pool, &mappings).await.unwrap();
    assert_eq!(result2[&("test.provider".into(), 1)], id1);
    assert_eq!(result2[&("test.provider".into(), 2)], id2);
}

// --- Descendants pagination ---

async fn insert_provider(pool: &PgPool, domain: &str, base_url: &str) {
    sqlx::query(
        "INSERT INTO commonfeed_providers (domain, name, base_url, max_results, status, enabled, api_key)
         VALUES ($1, 'Test', $2, 100, 'approved', true, 'test-key')",
    )
    .bind(domain)
    .bind(base_url)
    .execute(pool)
    .await
    .unwrap();
}

fn mock_post(id: i64, content: &str) -> serde_json::Value {
    serde_json::json!({
        "id": id,
        "url": format!("https://example.com/post/{id}"),
        "protocol": "activitypub",
        "identifiers": {},
        "type": "post",
        "content": format!("<p>{content}</p>"),
        "text": content,
        "author": {
            "handle": "@test@example.com",
            "name": "Test",
            "url": "https://example.com/@test",
            "avatar": null,
            "emojis": []
        },
        "timestamp": "2026-03-01T12:00:00Z",
        "engagement": { "likes": 0, "reposts": 0, "replies": 0 }
    })
}

#[sqlx::test]
async fn context_fetches_paginated_descendants(pool: PgPool) {
    use axum::extract::Query;
    use serde::Deserialize;
    use std::sync::Arc;
    use tokio::sync::Mutex;

    #[derive(Deserialize)]
    struct Params {
        cursor: Option<String>,
    }

    let call_count = Arc::new(Mutex::new(0u32));
    let call_count_clone = call_count.clone();

    let mock_router = axum::Router::new().route(
        "/posts/{id}/replies",
        get(move |Query(params): Query<Params>| {
            let call_count = call_count_clone.clone();
            async move {
                let mut count = call_count.lock().await;
                *count += 1;

                let (results, has_more, cursor) = match params.cursor.as_deref() {
                    None => (
                        vec![mock_post(1, "reply 1"), mock_post(2, "reply 2")],
                        true,
                        Some("page2"),
                    ),
                    Some("page2") => (vec![mock_post(3, "reply 3")], false, None),
                    _ => (vec![], false, None),
                };

                axum::Json(serde_json::json!({
                    "requestId": "test",
                    "results": results,
                    "pagination": {
                        "hasMore": has_more,
                        "cursor": cursor,
                    }
                }))
            }
        }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, mock_router).await.unwrap();
    });

    let mock_domain = "mock.provider";
    let base_url = format!("http://127.0.0.1:{port}");
    common::setup_db(&pool).await;
    insert_provider(&pool, mock_domain, &base_url).await;

    let parent = test_post("https://example.com/post/0", "@alice@example.com", "parent");
    let parent_id = map(&pool, mock_domain, 0, &parent).await;

    let app = common::TestApp::from_pool(pool).await;
    let resp = app
        .get(&format!("/api/v1/statuses/{parent_id}/context"))
        .await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    let descendants = json["descendants"].as_array().unwrap();
    assert_eq!(descendants.len(), 3, "should have fetched both pages");
    assert!(
        descendants[0]["content"]
            .as_str()
            .unwrap()
            .contains("reply 1")
    );
    assert!(
        descendants[1]["content"]
            .as_str()
            .unwrap()
            .contains("reply 2")
    );
    assert!(
        descendants[2]["content"]
            .as_str()
            .unwrap()
            .contains("reply 3")
    );

    let total_calls = *call_count.lock().await;
    assert_eq!(
        total_calls, 2,
        "should have made exactly 2 requests (2 pages)"
    );
}

// --- Mastodon proxy fallback ---

#[sqlx::test]
async fn detail_unknown_id_proxies_to_mastodon(pool: PgPool) {
    use axum::extract::Path;

    let mock_router = axum::Router::new().route(
        "/api/v1/statuses/{id}",
        get(|Path(id): Path<String>| async move {
            axum::Json(serde_json::json!({
                "id": id,
                "content": "<p>from mastodon</p>",
                "account": { "username": "native" }
            }))
        }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, mock_router).await.unwrap();
    });

    common::setup_db(&pool).await;
    let app =
        common::TestApp::from_pool_with_mastodon(pool, Some(format!("http://127.0.0.1:{port}")))
            .await;

    let resp = app.get("/api/v1/statuses/999999999999999999").await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    assert_eq!(json["id"], "999999999999999999");
    assert_eq!(json["content"], "<p>from mastodon</p>");
}

#[sqlx::test]
async fn context_unknown_id_proxies_to_mastodon(pool: PgPool) {
    use axum::extract::Path;

    let mock_router = axum::Router::new().route(
        "/api/v1/statuses/{id}/context",
        get(|Path(id): Path<String>| async move {
            axum::Json(serde_json::json!({
                "ancestors": [],
                "descendants": [{ "id": "1", "content": "native reply" }]
            }))
        }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, mock_router).await.unwrap();
    });

    common::setup_db(&pool).await;
    let app =
        common::TestApp::from_pool_with_mastodon(pool, Some(format!("http://127.0.0.1:{port}")))
            .await;

    let resp = app.get("/api/v1/statuses/999999999999999999/context").await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    let descendants = json["descendants"].as_array().unwrap();
    assert_eq!(descendants.len(), 1);
    assert_eq!(descendants[0]["content"], "native reply");
}

#[sqlx::test]
async fn proxy_forwards_authorization_header(pool: PgPool) {
    use axum::http::HeaderMap as AxumHeaderMap;
    use std::sync::Arc;
    use tokio::sync::Mutex;

    let received_auth = Arc::new(Mutex::new(None::<String>));
    let received_auth_clone = received_auth.clone();

    let mock_router = axum::Router::new().route(
        "/api/v1/statuses/{id}",
        get(move |headers: AxumHeaderMap| {
            let received = received_auth_clone.clone();
            async move {
                let auth = headers
                    .get("authorization")
                    .and_then(|v| v.to_str().ok())
                    .map(String::from);
                *received.lock().await = auth;
                axum::Json(serde_json::json!({"id": "1"}))
            }
        }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, mock_router).await.unwrap();
    });

    common::setup_db(&pool).await;
    let app =
        common::TestApp::from_pool_with_mastodon(pool, Some(format!("http://127.0.0.1:{port}")))
            .await;

    let req = axum::http::Request::get("/api/v1/statuses/999999999999999999")
        .header("authorization", "Bearer user_oauth_token_123")
        .body(axum::body::Body::empty())
        .unwrap();
    let resp = app.raw_request(req).await;
    assert_eq!(resp.status, StatusCode::OK);

    let forwarded = received_auth.lock().await;
    assert_eq!(
        forwarded.as_deref(),
        Some("Bearer user_oauth_token_123"),
        "authorization header must be forwarded to mastodon"
    );
}

#[sqlx::test]
async fn proxy_forwards_all_original_headers(pool: PgPool) {
    use axum::http::HeaderMap as AxumHeaderMap;
    use std::sync::Arc;
    use tokio::sync::Mutex;

    let received_headers = Arc::new(Mutex::new(AxumHeaderMap::new()));
    let received_clone = received_headers.clone();

    let mock_router = axum::Router::new().route(
        "/api/v1/statuses/{id}",
        get(move |headers: AxumHeaderMap| {
            let received = received_clone.clone();
            async move {
                *received.lock().await = headers;
                axum::Json(serde_json::json!({"id": "1"}))
            }
        }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, mock_router).await.unwrap();
    });

    common::setup_db(&pool).await;
    let app =
        common::TestApp::from_pool_with_mastodon(pool, Some(format!("http://127.0.0.1:{port}")))
            .await;

    let req = axum::http::Request::get("/api/v1/statuses/999999999999999999")
        .header("authorization", "Bearer test_token")
        .header("x-forwarded-proto", "https")
        .header("accept-language", "de")
        .body(axum::body::Body::empty())
        .unwrap();
    let resp = app.raw_request(req).await;
    assert_eq!(resp.status, StatusCode::OK);

    let headers = received_headers.lock().await;
    assert_eq!(
        headers.get("authorization").and_then(|v| v.to_str().ok()),
        Some("Bearer test_token"),
    );
    assert_eq!(
        headers
            .get("x-forwarded-proto")
            .and_then(|v| v.to_str().ok()),
        Some("https"),
    );
    assert_eq!(
        headers.get("accept-language").and_then(|v| v.to_str().ok()),
        Some("de"),
    );
}

#[sqlx::test]
async fn proxy_returns_mastodon_404_as_404(pool: PgPool) {
    let mock_router = axum::Router::new().route(
        "/api/v1/statuses/{id}",
        get(|| async { StatusCode::NOT_FOUND }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, mock_router).await.unwrap();
    });

    common::setup_db(&pool).await;
    let app =
        common::TestApp::from_pool_with_mastodon(pool, Some(format!("http://127.0.0.1:{port}")))
            .await;

    let resp = app.get("/api/v1/statuses/999999999999999999").await;
    assert_eq!(resp.status, StatusCode::NOT_FOUND);
}
