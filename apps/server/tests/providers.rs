mod common;

/// Test that provider management DB operations work correctly.
/// These test the state crate's provider functions against a real database.

#[tokio::test]
async fn upsert_provider_and_find() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    state::providers::upsert(
        app.pool(),
        "feeds.example.com",
        "Example Feeds",
        "https://feeds.example.com/api/v1",
        100,
    )
    .await
    .unwrap();

    let base_url = state::providers::find_base_url(app.pool(), "feeds.example.com")
        .await
        .unwrap();

    assert_eq!(
        base_url.as_deref(),
        Some("https://feeds.example.com/api/v1")
    );
}

#[tokio::test]
async fn upsert_provider_is_idempotent() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    state::providers::upsert(
        app.pool(),
        "feeds.example.com",
        "V1",
        "https://feeds.example.com/v1",
        100,
    )
    .await
    .unwrap();

    state::providers::upsert(
        app.pool(),
        "feeds.example.com",
        "V2",
        "https://feeds.example.com/v2",
        200,
    )
    .await
    .unwrap();

    let base_url = state::providers::find_base_url(app.pool(), "feeds.example.com")
        .await
        .unwrap();
    assert_eq!(
        base_url.as_deref(),
        Some("https://feeds.example.com/v2"),
        "second upsert should update"
    );
}

#[tokio::test]
async fn find_sources_returns_empty_when_no_providers() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    let sources = state::providers::find_sources(app.pool(), "trends/statuses").await;
    assert!(sources.is_empty());
}

#[tokio::test]
async fn enable_source_and_find() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    // Set up provider
    state::providers::upsert(
        app.pool(),
        "feeds.example.com",
        "Example",
        "https://feeds.example.com/api/v1",
        100,
    )
    .await
    .unwrap();

    // Approve it
    state::providers::update_status(app.pool(), "feeds.example.com", "approved")
        .await
        .unwrap();

    // Give it an API key
    state::providers::save_registration(
        app.pool(),
        "feeds.example.com",
        "cf_live_test_key",
        "req_001",
        "approved",
        "/.well-known/commonfeed/verify",
    )
    .await
    .unwrap();

    // Add capability
    state::providers::upsert_capability(
        app.pool(),
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

    // Enable as source for trends/statuses route
    state::providers::enable_source(
        app.pool(),
        "trends/statuses",
        "feeds.example.com",
        "posts",
        "trending",
    )
    .await
    .unwrap();

    // Should now find the source
    let sources = state::providers::find_sources(app.pool(), "trends/statuses").await;
    assert_eq!(sources.len(), 1);
    assert_eq!(sources[0].provider.domain, "feeds.example.com");
    assert_eq!(sources[0].algorithm, "trending");
}

#[tokio::test]
async fn disable_source() {
    let Some(app) = common::TestApp::spawn().await else {
        eprintln!("SKIPPED: infrastructure not available");
        return;
    };

    // Full setup
    state::providers::upsert(
        app.pool(),
        "feeds.example.com",
        "Example",
        "https://feeds.example.com/api/v1",
        100,
    )
    .await
    .unwrap();
    state::providers::update_status(app.pool(), "feeds.example.com", "approved")
        .await
        .unwrap();
    state::providers::save_registration(
        app.pool(),
        "feeds.example.com",
        "cf_live_test",
        "req_001",
        "approved",
        "/verify",
    )
    .await
    .unwrap();
    state::providers::upsert_capability(
        app.pool(),
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
        app.pool(),
        "trends/statuses",
        "feeds.example.com",
        "posts",
        "trending",
    )
    .await
    .unwrap();

    // Disable
    let affected =
        state::providers::disable_source(app.pool(), "trends/statuses", "feeds.example.com")
            .await
            .unwrap();
    assert_eq!(affected, 1);

    // Should be empty now
    let sources = state::providers::find_sources(app.pool(), "trends/statuses").await;
    assert!(sources.is_empty());
}
