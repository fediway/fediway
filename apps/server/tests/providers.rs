mod common;

use sqlx::PgPool;

#[sqlx::test]
async fn upsert_provider_and_find(pool: PgPool) {
    common::setup_db(&pool).await;
    state::providers::upsert(
        &pool,
        "feeds.example.com",
        "Example Feeds",
        "https://feeds.example.com/api/v1",
        100,
    )
    .await
    .unwrap();

    let base_url = state::providers::find_base_url(&pool, "feeds.example.com")
        .await
        .unwrap();

    assert_eq!(
        base_url.as_deref(),
        Some("https://feeds.example.com/api/v1")
    );
}

#[sqlx::test]
async fn upsert_provider_is_idempotent(pool: PgPool) {
    common::setup_db(&pool).await;
    state::providers::upsert(
        &pool,
        "feeds.example.com",
        "V1",
        "https://feeds.example.com/v1",
        100,
    )
    .await
    .unwrap();

    state::providers::upsert(
        &pool,
        "feeds.example.com",
        "V2",
        "https://feeds.example.com/v2",
        200,
    )
    .await
    .unwrap();

    let base_url = state::providers::find_base_url(&pool, "feeds.example.com")
        .await
        .unwrap();
    assert_eq!(
        base_url.as_deref(),
        Some("https://feeds.example.com/v2"),
        "second upsert should update"
    );
}

#[sqlx::test]
async fn find_sources_returns_empty_when_no_providers(pool: PgPool) {
    common::setup_db(&pool).await;
    let sources = state::providers::find_sources(&pool, "trends/statuses").await;
    assert!(sources.is_empty());
}

#[sqlx::test]
async fn enable_source_and_find(pool: PgPool) {
    common::setup_db(&pool).await;
    state::providers::upsert(
        &pool,
        "feeds.example.com",
        "Example",
        "https://feeds.example.com/api/v1",
        100,
    )
    .await
    .unwrap();

    state::providers::update_status(&pool, "feeds.example.com", "approved")
        .await
        .unwrap();

    state::providers::save_registration(
        &pool,
        "feeds.example.com",
        "cf_live_test_key",
        "req_001",
        "approved",
        "/.well-known/commonfeed/verify",
    )
    .await
    .unwrap();

    state::providers::upsert_capability(
        &pool,
        &state::providers::Capability {
            provider_domain: "feeds.example.com",
            resource: "posts",
            algorithm: "trending",
            description: "Trending posts",
            filters: &["language".into()],
            embedding_required: None,
            embedding_models: None,
        },
    )
    .await
    .unwrap();

    state::providers::enable_source(
        &pool,
        "trends/statuses",
        "feeds.example.com",
        "posts",
        "trending",
    )
    .await
    .unwrap();

    let sources = state::providers::find_sources(&pool, "trends/statuses").await;
    assert_eq!(sources.len(), 1);
    assert_eq!(sources[0].provider.domain, "feeds.example.com");
    assert_eq!(sources[0].algorithm, "trending");
}

#[sqlx::test]
async fn disable_source(pool: PgPool) {
    common::setup_db(&pool).await;
    state::providers::upsert(
        &pool,
        "feeds.example.com",
        "Example",
        "https://feeds.example.com/api/v1",
        100,
    )
    .await
    .unwrap();
    state::providers::update_status(&pool, "feeds.example.com", "approved")
        .await
        .unwrap();
    state::providers::save_registration(
        &pool,
        "feeds.example.com",
        "cf_live_test",
        "req_001",
        "approved",
        "/verify",
    )
    .await
    .unwrap();
    state::providers::upsert_capability(
        &pool,
        &state::providers::Capability {
            provider_domain: "feeds.example.com",
            resource: "posts",
            algorithm: "trending",
            description: "Trending",
            filters: &[],
            embedding_required: None,
            embedding_models: None,
        },
    )
    .await
    .unwrap();
    state::providers::enable_source(
        &pool,
        "trends/statuses",
        "feeds.example.com",
        "posts",
        "trending",
    )
    .await
    .unwrap();

    let affected = state::providers::disable_source(&pool, "trends/statuses", "feeds.example.com")
        .await
        .unwrap();
    assert_eq!(affected, 1);

    let sources = state::providers::find_sources(&pool, "trends/statuses").await;
    assert!(sources.is_empty());
}
