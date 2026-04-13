mod common;

use axum::http::StatusCode;
use sqlx::PgPool;

async fn insert_account(pool: &PgPool, username: &str, domain: Option<&str>) -> i64 {
    let url = match domain {
        Some(d) => format!("https://{d}/@{username}"),
        None => format!("https://test.example.com/@{username}"),
    };
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO accounts (username, domain, display_name, url)
         VALUES ($1, $2, $1, $3) RETURNING id",
    )
    .bind(username)
    .bind(domain)
    .bind(url)
    .fetch_one(pool)
    .await
    .unwrap()
}

async fn insert_status(
    pool: &PgPool,
    account_id: i64,
    uri: &str,
    text: &str,
    visibility: i32,
) -> i64 {
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO statuses (account_id, uri, url, text, visibility)
         VALUES ($1, $2, $2, $3, $4) RETURNING id",
    )
    .bind(account_id)
    .bind(uri)
    .bind(text)
    .bind(visibility)
    .fetch_one(pool)
    .await
    .unwrap()
}

async fn insert_tag(pool: &PgPool, name: &str) -> i64 {
    sqlx::query_scalar::<_, i64>("INSERT INTO tags (name) VALUES ($1) RETURNING id")
        .bind(name)
        .fetch_one(pool)
        .await
        .unwrap()
}

async fn link_tag(pool: &PgPool, status_id: i64, tag_id: i64) {
    sqlx::query("INSERT INTO statuses_tags (status_id, tag_id) VALUES ($1, $2)")
        .bind(status_id)
        .bind(tag_id)
        .execute(pool)
        .await
        .unwrap();
}

async fn seed_tagged_public(
    pool: &PgPool,
    account_id: i64,
    uri: &str,
    text: &str,
    tag_id: i64,
) -> i64 {
    let id = insert_status(pool, account_id, uri, text, 0).await;
    link_tag(pool, id, tag_id).await;
    id
}

#[sqlx::test]
async fn tag_timeline_empty_returns_empty_array(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get("/api/v1/timelines/tag/rust").await;
    assert_eq!(resp.status, StatusCode::OK);

    let json = resp.json();
    let statuses = json.as_array().expect("expected array response");
    assert!(statuses.is_empty());
}

#[sqlx::test]
async fn tag_timeline_returns_native_status(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "rust").await;
    let status_id = seed_tagged_public(
        &pool,
        alice,
        "https://test.example.com/users/alice/statuses/1",
        "hello rust",
        tag,
    )
    .await;

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get("/api/v1/timelines/tag/rust").await;
    assert_eq!(resp.status, StatusCode::OK);

    let statuses = resp.json();
    let arr = statuses.as_array().unwrap();
    assert_eq!(arr.len(), 1);
    assert_eq!(arr[0]["id"], status_id.to_string());
    assert!(arr[0]["content"].as_str().unwrap().contains("hello rust"));
    assert_eq!(arr[0]["account"]["username"], "alice");
}

#[sqlx::test]
async fn tag_timeline_returns_federated_status(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let bob = insert_account(&pool, "bob", Some("remote.example")).await;
    let tag = insert_tag(&pool, "rust").await;
    seed_tagged_public(
        &pool,
        bob,
        "https://remote.example/users/bob/statuses/1",
        "federated rust",
        tag,
    )
    .await;

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get("/api/v1/timelines/tag/rust").await;
    assert_eq!(resp.status, StatusCode::OK);

    let arr = resp.json();
    let arr = arr.as_array().unwrap();
    assert_eq!(arr.len(), 1);
    assert!(
        arr[0]["content"]
            .as_str()
            .unwrap()
            .contains("federated rust")
    );
}

#[sqlx::test]
async fn tag_timeline_mixes_native_and_federated(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let bob = insert_account(&pool, "bob", Some("remote.example")).await;
    let tag = insert_tag(&pool, "rust").await;

    for i in 0..3 {
        seed_tagged_public(
            &pool,
            alice,
            &format!("https://test.example.com/users/alice/statuses/{i}"),
            &format!("native {i}"),
            tag,
        )
        .await;
    }
    for i in 0..3 {
        seed_tagged_public(
            &pool,
            bob,
            &format!("https://remote.example/users/bob/statuses/{i}"),
            &format!("federated {i}"),
            tag,
        )
        .await;
    }

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get("/api/v1/timelines/tag/rust").await;
    assert_eq!(resp.status, StatusCode::OK);

    let arr = resp.json();
    let arr = arr.as_array().unwrap();
    assert!(
        arr.len() >= 4,
        "expected at least 4 mixed results, got {}",
        arr.len()
    );

    let contents: Vec<&str> = arr.iter().filter_map(|s| s["content"].as_str()).collect();
    assert!(
        contents.iter().any(|c| c.contains("native")),
        "native content missing"
    );
    assert!(
        contents.iter().any(|c| c.contains("federated")),
        "federated content missing"
    );
}

#[sqlx::test]
async fn tag_timeline_dedupes_shared_uri_preferring_native(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let bob = insert_account(&pool, "bob", Some("remote.example")).await;
    let tag = insert_tag(&pool, "rust").await;

    let shared_uri = "https://shared.example/statuses/shared";
    seed_tagged_public(&pool, alice, shared_uri, "native version", tag).await;
    seed_tagged_public(&pool, bob, shared_uri, "federated version", tag).await;

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get("/api/v1/timelines/tag/rust").await;
    assert_eq!(resp.status, StatusCode::OK);

    let arr = resp.json();
    let arr = arr.as_array().unwrap();
    assert_eq!(arr.len(), 1, "shared URI must be deduped");
    assert_eq!(arr[0]["account"]["username"], "alice");
    assert!(
        arr[0]["content"]
            .as_str()
            .unwrap()
            .contains("native version"),
        "priority dedup must keep the native version"
    );
}

#[sqlx::test]
async fn tag_timeline_excludes_private_visibility(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "rust").await;
    let private = insert_status(
        &pool,
        alice,
        "https://test.example.com/1",
        "private post",
        2,
    )
    .await;
    link_tag(&pool, private, tag).await;

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get("/api/v1/timelines/tag/rust").await;
    assert_eq!(resp.status, StatusCode::OK);

    let arr = resp.json();
    assert!(
        arr.as_array().unwrap().is_empty(),
        "private posts must not appear in tag timelines"
    );
}

#[sqlx::test]
async fn tag_timeline_respects_limit_param(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "rust").await;
    for i in 0..10 {
        seed_tagged_public(
            &pool,
            alice,
            &format!("https://test.example.com/statuses/{i}"),
            &format!("post {i}"),
            tag,
        )
        .await;
    }

    let app = common::TestApp::from_pool(pool).await;
    let resp = app.get("/api/v1/timelines/tag/rust?limit=3").await;
    assert_eq!(resp.status, StatusCode::OK);

    let arr = resp.json();
    assert_eq!(arr.as_array().unwrap().len(), 3);
}
