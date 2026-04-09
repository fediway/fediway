mod common;

use axum::http::StatusCode;
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
    let url = post["url"].as_str().unwrap();
    state::statuses::map_post(pool, domain, remote_id, url, url, post)
        .await
        .expect("map_post failed")
}

// --- Error cases ---

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
async fn detail_unknown_id_returns_404(pool: PgPool) {
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get("/api/v1/statuses/999999999999999999").await;
    assert_eq!(resp.status, StatusCode::NOT_FOUND);
}

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
async fn detail_non_numeric_id_returns_404(pool: PgPool) {
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get("/api/v1/statuses/not-a-number").await;
    assert_eq!(resp.status, StatusCode::NOT_FOUND);
}

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
async fn context_unknown_id_returns_404(pool: PgPool) {
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get("/api/v1/statuses/999999999999999999/context").await;
    assert_eq!(resp.status, StatusCode::NOT_FOUND);
}

// --- Detail happy path ---

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
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

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
async fn detail_same_post_returns_same_id(pool: PgPool) {
    let post = test_post("https://example.com/post/1", "@test@example.com", "test");

    let id1 = map(&pool, "test.provider", 99, &post).await;
    let id2 = map(&pool, "test.provider", 99, &post).await;

    assert_eq!(
        id1, id2,
        "same provider + remote_id must return same snowflake"
    );
}

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
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

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
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

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
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

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
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

#[sqlx::test(migrations = "../../crates/state/src/migrations")]
async fn batch_map_posts_returns_consistent_ids(pool: PgPool) {
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
