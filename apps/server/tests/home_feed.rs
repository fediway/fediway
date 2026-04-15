mod common;

use std::time::Duration;

use feed::Feed;
use server::auth::{Account, BearerToken};
use server::feeds::HomeFeed;
use server::state::AppStateInner;
use sources::commonfeed::types::QueryFilters;
use sources::mastodon::MediaConfig;
use sqlx::PgPool;
use state::cache::Cache;
use state::feed_store::FeedStore;

async fn insert_account(pool: &PgPool, username: &str) -> i64 {
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO accounts (username, display_name, url)
         VALUES ($1, $1, $2) RETURNING id",
    )
    .bind(username)
    .bind(format!("https://local.test/@{username}"))
    .fetch_one(pool)
    .await
    .unwrap()
}

async fn insert_status(pool: &PgPool, account_id: i64, text: &str) -> i64 {
    let uri = format!("https://local.test/statuses/{text}");
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO statuses (account_id, uri, text, visibility)
         VALUES ($1, $2, $3, 0) RETURNING id",
    )
    .bind(account_id)
    .bind(&uri)
    .bind(text)
    .fetch_one(pool)
    .await
    .unwrap()
}

async fn insert_favourite(pool: &PgPool, account_id: i64, status_id: i64) {
    sqlx::query("INSERT INTO favourites (account_id, status_id) VALUES ($1, $2)")
        .bind(account_id)
        .bind(status_id)
        .execute(pool)
        .await
        .unwrap();
}

async fn insert_status_stats(pool: &PgPool, status_id: i64, favourites_count: i64) {
    sqlx::query(
        "INSERT INTO status_stats (status_id, favourites_count, reblogs_count)
         VALUES ($1, $2, 0)",
    )
    .bind(status_id)
    .bind(favourites_count)
    .execute(pool)
    .await
    .unwrap();
}

fn account_for(id: i64, username: &str) -> Account {
    Account {
        id,
        username: username.into(),
        chosen_languages: Vec::new(),
        token: BearerToken::new(String::new()),
    }
}

#[sqlx::test]
async fn home_feed_surfaces_network_candidates(pool: PgPool) {
    common::setup_db(&pool).await;
    common::setup_mastodon_schema(&pool).await;

    let viewer_id = insert_account(&pool, "viewer").await;
    let alice_id = insert_account(&pool, "alice").await;

    let seed = insert_status(&pool, alice_id, "old-engagement").await;
    insert_favourite(&pool, viewer_id, seed).await;

    let candidate = insert_status(&pool, alice_id, "fresh-network-post").await;
    insert_status_stats(&pool, candidate, 5).await;

    let viewer = account_for(viewer_id, "viewer");
    let feed_store = FeedStore::new(Cache::disabled(), Duration::from_secs(60));
    let media = MediaConfig::new("local.test".into(), false);
    let state = AppStateInner::new(
        pool,
        feed_store,
        media,
        "nomic_v1.5_64d".into(),
        "local.test".into(),
        None,
    );

    let feed = HomeFeed::new(&state, &viewer, QueryFilters::default()).await;
    let candidates = feed.collect().await;

    assert!(
        candidates
            .iter()
            .any(|c| c.item.text == "fresh-network-post"),
        "the fresh in-network post must appear in the home feed surface"
    );
}

#[sqlx::test]
async fn home_feed_cold_start_does_not_panic(pool: PgPool) {
    common::setup_db(&pool).await;
    common::setup_mastodon_schema(&pool).await;

    let viewer_id = insert_account(&pool, "viewer").await;
    let viewer = account_for(viewer_id, "viewer");
    let feed_store = FeedStore::new(Cache::disabled(), Duration::from_secs(60));
    let media = MediaConfig::new("local.test".into(), false);
    let state = AppStateInner::new(
        pool,
        feed_store,
        media,
        "nomic_v1.5_64d".into(),
        "local.test".into(),
        None,
    );

    let feed = HomeFeed::new(&state, &viewer, QueryFilters::default()).await;
    let _ = feed.collect().await;
}
