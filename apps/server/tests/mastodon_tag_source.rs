mod common;

use feed::source::Source;
use sources::mastodon::{FederatedTagSource, NativeTagSource};
use sqlx::PgPool;

async fn insert_account(pool: &PgPool, username: &str, domain: Option<&str>) -> i64 {
    let url = match domain {
        Some(d) => format!("https://{d}/@{username}"),
        None => format!("https://local.test/@{username}"),
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
    text: &str,
    visibility: i32,
    reblog_of_id: Option<i64>,
) -> i64 {
    let uri = format!("https://any.test/statuses/{text}");
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO statuses (account_id, uri, url, text, visibility, reblog_of_id)
         VALUES ($1, $2, $2, $3, $4, $5) RETURNING id",
    )
    .bind(account_id)
    .bind(&uri)
    .bind(text)
    .bind(visibility)
    .bind(reblog_of_id)
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

async fn seed_tagged(pool: &PgPool, account_id: i64, text: &str, tag_id: i64) -> i64 {
    let id = insert_status(pool, account_id, text, 0, None).await;
    link_tag(pool, id, tag_id).await;
    id
}

#[sqlx::test]
async fn native_source_returns_only_native_accounts(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let bob = insert_account(&pool, "bob", Some("remote.example")).await;
    let tag = insert_tag(&pool, "rust").await;
    seed_tagged(&pool, alice, "native post", tag).await;
    seed_tagged(&pool, bob, "federated post", tag).await;

    let source = NativeTagSource::new(pool, "rust".into(), "local.test".into());
    let candidates = source.collect(10).await;

    assert_eq!(candidates.len(), 1);
    assert_eq!(candidates[0].item.text, "native post");
    assert_eq!(candidates[0].item.author.handle, "alice@local.test");
}

#[sqlx::test]
async fn federated_source_returns_only_non_native_accounts(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let bob = insert_account(&pool, "bob", Some("remote.example")).await;
    let tag = insert_tag(&pool, "rust").await;
    seed_tagged(&pool, alice, "native post", tag).await;
    seed_tagged(&pool, bob, "federated post", tag).await;

    let source = FederatedTagSource::new(pool, "rust".into(), "local.test".into());
    let candidates = source.collect(10).await;

    assert_eq!(candidates.len(), 1);
    assert_eq!(candidates[0].item.text, "federated post");
    assert_eq!(candidates[0].item.author.handle, "bob@remote.example");
}

#[sqlx::test]
async fn native_source_excludes_private_visibility(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "rust").await;

    let private = insert_status(&pool, alice, "private post", 2, None).await;
    link_tag(&pool, private, tag).await;
    let unlisted = insert_status(&pool, alice, "unlisted post", 1, None).await;
    link_tag(&pool, unlisted, tag).await;

    let source = NativeTagSource::new(pool, "rust".into(), "local.test".into());
    let candidates = source.collect(10).await;

    assert_eq!(candidates.len(), 1);
    assert_eq!(candidates[0].item.text, "unlisted post");
}

#[sqlx::test]
async fn native_source_excludes_reblogs(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "rust").await;
    let original = seed_tagged(&pool, alice, "original", tag).await;
    let reblog = insert_status(&pool, alice, "a reblog", 0, Some(original)).await;
    link_tag(&pool, reblog, tag).await;

    let source = NativeTagSource::new(pool, "rust".into(), "local.test".into());
    let candidates = source.collect(10).await;

    assert_eq!(candidates.len(), 1);
    assert_eq!(candidates[0].item.text, "original");
}

#[sqlx::test]
async fn native_source_respects_limit(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "rust").await;
    for i in 0..5 {
        seed_tagged(&pool, alice, &format!("post {i}"), tag).await;
    }

    let source = NativeTagSource::new(pool, "rust".into(), "local.test".into());
    let candidates = source.collect(2).await;
    assert_eq!(candidates.len(), 2);
}

#[sqlx::test]
async fn native_source_empty_for_unknown_tag(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "rust").await;
    seed_tagged(&pool, alice, "post", tag).await;

    let source = NativeTagSource::new(pool, "nonexistent".into(), "local.test".into());
    let candidates = source.collect(10).await;
    assert!(candidates.is_empty());
}

#[sqlx::test]
async fn native_source_matches_tag_case_insensitively(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "Rust").await;
    seed_tagged(&pool, alice, "post", tag).await;

    let source = NativeTagSource::new(pool, "RUST".into(), "local.test".into());
    let candidates = source.collect(10).await;
    assert_eq!(candidates.len(), 1);
}

#[sqlx::test]
async fn native_source_sets_provider_fields_for_local_roundtrip(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "rust").await;
    let status_id = seed_tagged(&pool, alice, "post", tag).await;

    let source = NativeTagSource::new(pool, "rust".into(), "local.test".into());
    let candidates = source.collect(10).await;

    assert_eq!(candidates.len(), 1);
    let post = &candidates[0].item;
    assert_eq!(post.provider_domain.as_deref(), Some("local.test"));
    assert_eq!(post.provider_id, Some(status_id));
}

#[sqlx::test]
async fn native_source_orders_by_created_at_desc(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let alice = insert_account(&pool, "alice", None).await;
    let tag = insert_tag(&pool, "rust").await;

    let old = seed_tagged(&pool, alice, "old", tag).await;
    sqlx::query("UPDATE statuses SET created_at = NOW() - INTERVAL '1 day' WHERE id = $1")
        .bind(old)
        .execute(&pool)
        .await
        .unwrap();
    seed_tagged(&pool, alice, "new", tag).await;

    let source = NativeTagSource::new(pool, "rust".into(), "local.test".into());
    let candidates = source.collect(10).await;

    assert_eq!(candidates.len(), 2);
    assert_eq!(candidates[0].item.text, "new");
    assert_eq!(candidates[1].item.text, "old");
}
