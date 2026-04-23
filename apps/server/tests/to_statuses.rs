mod common;

use ::common::ids::AccountId;
use sources::mastodon::CachedPost;
use sqlx::PgPool;

async fn insert_account(pool: &PgPool, username: &str, display_name: &str) -> i64 {
    let url = format!("https://local.test/@{username}");
    let uri = format!("https://local.test/users/{username}");
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO accounts
            (username, domain, display_name, note, url, uri, avatar_file_name, header_file_name, actor_type)
         VALUES ($1, NULL, $2, '', $3, $4, 'avatar.jpg', 'header.jpg', 'Person')
         RETURNING id",
    )
    .bind(username)
    .bind(display_name)
    .bind(&url)
    .bind(&uri)
    .fetch_one(pool)
    .await
    .expect("insert account")
}

async fn insert_account_stats(
    pool: &PgPool,
    account_id: i64,
    statuses: i64,
    followers: i64,
    following: i64,
) {
    sqlx::query(
        "INSERT INTO account_stats (account_id, statuses_count, followers_count, following_count)
         VALUES ($1, $2, $3, $4)",
    )
    .bind(account_id)
    .bind(statuses)
    .bind(followers)
    .bind(following)
    .execute(pool)
    .await
    .expect("insert account_stats");
}

async fn insert_status(pool: &PgPool, account_id: i64, text: &str) -> i64 {
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO statuses (account_id, uri, url, text, spoiler_text, visibility)
         VALUES ($1, NULL, NULL, $2, '', 0)
         RETURNING id",
    )
    .bind(account_id)
    .bind(text)
    .fetch_one(pool)
    .await
    .expect("insert status")
}

#[sqlx::test]
async fn to_statuses_promotes_resolved_remote_to_fetch_by_ids(pool: PgPool) {
    common::setup_db(&pool).await;
    common::setup_mastodon_schema(&pool).await;

    let author = insert_account(&pool, "remauthor", "Remote Author").await;
    insert_account_stats(&pool, author, 1, 0, 0).await;
    let viewer = insert_account(&pool, "remviewer", "Remote Viewer").await;
    insert_account_stats(&pool, viewer, 0, 0, 0).await;

    let mastodon_status_id = insert_status(&pool, author, "resolved content").await;
    sqlx::query("INSERT INTO favourites (account_id, status_id) VALUES ($1, $2)")
        .bind(viewer)
        .bind(mastodon_status_id)
        .execute(&pool)
        .await
        .unwrap();

    let post_json = serde_json::json!({
        "provider_id": 8_001_i64,
        "provider_domain": "remote.example",
        "uri": "https://remote.example/post/8001",
        "url": "https://remote.example/post/8001",
        "content": "<p>remote content</p>",
        "text": "remote content",
        "author": {
            "handle": "@remauthor@remote.example",
            "display_name": "Remote Author",
            "url": "https://remote.example/@remauthor",
            "emojis": []
        },
        "published_at": "2026-04-15T12:00:00Z",
        "sensitive": false,
        "media": [],
        "engagement": { "replies": 0, "reposts": 0, "likes": 0 },
        "tags": [],
        "emojis": []
    });

    let snowflake = state::statuses::map_post(
        &pool,
        "remote.example",
        8_001,
        "https://remote.example/post/8001",
        "https://remote.example/post/8001",
        &post_json,
    )
    .await
    .unwrap();
    state::statuses::set_mastodon_local_id(&pool, snowflake, mastodon_status_id)
        .await
        .unwrap();

    let post: ::common::types::Post = serde_json::from_value(post_json).unwrap();

    let media = common::test_media();
    let out = server::mastodon::statuses::to_statuses(
        &pool,
        "local.test",
        &media,
        vec![CachedPost::Remote {
            post: Box::new(post),
        }],
        Some(AccountId(viewer)),
    )
    .await
    .expect("to_statuses should succeed");

    assert_eq!(out.len(), 1);
    assert_eq!(
        out[0].id,
        mastodon_status_id.to_string(),
        "resolved remote must be served via fetch_by_ids with Mastodon's native id, not a snowflake-URL fallback"
    );
    assert!(
        out[0].favourited,
        "resolved remote must pick up viewer state through fetch_by_ids — Status::from_post hardcodes favourited=false"
    );
    assert_eq!(
        out[0].text.as_deref(),
        Some("resolved content"),
        "content must come from Mastodon's statuses table, not the cached post_data"
    );
}

#[sqlx::test]
async fn to_statuses_threads_viewer_state_through_to_local_statuses(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;

    let author = insert_account(&pool, "author", "Author").await;
    insert_account_stats(&pool, author, 1, 0, 0).await;
    let viewer = insert_account(&pool, "viewer", "Viewer").await;
    insert_account_stats(&pool, viewer, 0, 0, 0).await;

    let status_id = insert_status(&pool, author, "favourited via to_statuses").await;
    sqlx::query("INSERT INTO favourites (account_id, status_id) VALUES ($1, $2)")
        .bind(viewer)
        .bind(status_id)
        .execute(&pool)
        .await
        .unwrap();

    let media = common::test_media();
    let out = server::mastodon::statuses::to_statuses(
        &pool,
        "local.test",
        &media,
        vec![CachedPost::Local { id: status_id }],
        Some(AccountId(viewer)),
    )
    .await
    .expect("to_statuses should succeed");

    assert_eq!(out.len(), 1);
    assert!(
        out[0].favourited,
        "to_statuses must pass the viewer down to fetch_by_ids so per-user state reaches timeline responses"
    );
}

#[sqlx::test]
async fn to_statuses_without_viewer_leaves_state_false(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;

    let author = insert_account(&pool, "author", "Author").await;
    insert_account_stats(&pool, author, 1, 0, 0).await;
    let other = insert_account(&pool, "other", "Other").await;
    insert_account_stats(&pool, other, 0, 0, 0).await;

    let status_id = insert_status(&pool, author, "post").await;
    sqlx::query("INSERT INTO favourites (account_id, status_id) VALUES ($1, $2)")
        .bind(other)
        .bind(status_id)
        .execute(&pool)
        .await
        .unwrap();

    let media = common::test_media();
    let out = server::mastodon::statuses::to_statuses(
        &pool,
        "local.test",
        &media,
        vec![CachedPost::Local { id: status_id }],
        None,
    )
    .await
    .expect("to_statuses should succeed");

    assert_eq!(out.len(), 1);
    assert!(!out[0].favourited);
}
