mod common;

use feed::source::Source;
use sources::mastodon::NetworkSource;
use sqlx::PgPool;

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

async fn insert_account_with_domain(pool: &PgPool, username: &str, domain: &str) -> i64 {
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO accounts (username, domain, display_name, url)
         VALUES ($1, $2, $1, $3) RETURNING id",
    )
    .bind(username)
    .bind(domain)
    .bind(format!("https://{domain}/@{username}"))
    .fetch_one(pool)
    .await
    .unwrap()
}

async fn mark_account_suspended(pool: &PgPool, account_id: i64) {
    sqlx::query("UPDATE accounts SET suspended_at = NOW() WHERE id = $1")
        .bind(account_id)
        .execute(pool)
        .await
        .unwrap();
}

async fn mark_account_silenced(pool: &PgPool, account_id: i64) {
    sqlx::query("UPDATE accounts SET silenced_at = NOW() WHERE id = $1")
        .bind(account_id)
        .execute(pool)
        .await
        .unwrap();
}

async fn mark_status_deleted(pool: &PgPool, status_id: i64) {
    sqlx::query("UPDATE statuses SET deleted_at = NOW() WHERE id = $1")
        .bind(status_id)
        .execute(pool)
        .await
        .unwrap();
}

async fn insert_block(pool: &PgPool, account_id: i64, target_account_id: i64) {
    sqlx::query("INSERT INTO blocks (account_id, target_account_id) VALUES ($1, $2)")
        .bind(account_id)
        .bind(target_account_id)
        .execute(pool)
        .await
        .unwrap();
}

async fn insert_mute(pool: &PgPool, account_id: i64, target_account_id: i64) {
    sqlx::query("INSERT INTO mutes (account_id, target_account_id) VALUES ($1, $2)")
        .bind(account_id)
        .bind(target_account_id)
        .execute(pool)
        .await
        .unwrap();
}

async fn insert_domain_block(pool: &PgPool, account_id: i64, domain: &str) {
    sqlx::query("INSERT INTO account_domain_blocks (account_id, domain) VALUES ($1, $2)")
        .bind(account_id)
        .bind(domain)
        .execute(pool)
        .await
        .unwrap();
}

async fn insert_status_with_visibility(
    pool: &PgPool,
    account_id: i64,
    text: &str,
    visibility: i32,
) -> i64 {
    let uri = format!("https://local.test/statuses/{text}");
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO statuses (account_id, uri, text, visibility)
         VALUES ($1, $2, $3, $4) RETURNING id",
    )
    .bind(account_id)
    .bind(&uri)
    .bind(text)
    .bind(visibility)
    .fetch_one(pool)
    .await
    .unwrap()
}

async fn insert_reply(
    pool: &PgPool,
    account_id: i64,
    text: &str,
    in_reply_to_id: i64,
    in_reply_to_account_id: i64,
) -> i64 {
    let uri = format!("https://local.test/statuses/{text}");
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO statuses (account_id, uri, text, visibility, in_reply_to_id, in_reply_to_account_id)
         VALUES ($1, $2, $3, 0, $4, $5) RETURNING id",
    )
    .bind(account_id)
    .bind(&uri)
    .bind(text)
    .bind(in_reply_to_id)
    .bind(in_reply_to_account_id)
    .fetch_one(pool)
    .await
    .unwrap()
}

async fn insert_reblog(pool: &PgPool, account_id: i64, text: &str, reblog_of_id: i64) -> i64 {
    let uri = format!("https://local.test/statuses/{text}");
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO statuses (account_id, uri, text, visibility, reblog_of_id)
         VALUES ($1, $2, $3, 0, $4) RETURNING id",
    )
    .bind(account_id)
    .bind(&uri)
    .bind(text)
    .bind(reblog_of_id)
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

async fn insert_status_stats(
    pool: &PgPool,
    status_id: i64,
    favourites_count: i64,
    reblogs_count: i64,
) {
    sqlx::query(
        "INSERT INTO status_stats (status_id, favourites_count, reblogs_count)
         VALUES ($1, $2, $3)",
    )
    .bind(status_id)
    .bind(favourites_count)
    .bind(reblogs_count)
    .execute(pool)
    .await
    .unwrap();
}

async fn insert_follow(pool: &PgPool, follower: i64, target: i64) {
    sqlx::query("INSERT INTO follows (account_id, target_account_id) VALUES ($1, $2)")
        .bind(follower)
        .bind(target)
        .execute(pool)
        .await
        .unwrap();
}

#[sqlx::test]
async fn cold_start_returns_empty(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.is_empty(),
        "cold-start user should get no candidates"
    );
}

#[sqlx::test]
async fn runs_full_pipeline_against_seeded_db(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;

    let seed = insert_status(&pool, alice, "seed").await;
    insert_favourite(&pool, user, seed).await;

    let candidate = insert_status(&pool, alice, "recent").await;
    insert_status_stats(&pool, candidate, 5, 2).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        !candidates.is_empty(),
        "expected at least one candidate from alice"
    );
    assert!(
        candidates.iter().any(|c| c.item.text == "recent"),
        "the freshly-engaged status should appear"
    );
}

#[sqlx::test]
async fn direct_messages_excluded_from_candidates(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;

    let public_seed = insert_status(&pool, alice, "public").await;
    insert_favourite(&pool, user, public_seed).await;
    let dm = insert_status_with_visibility(&pool, alice, "secret-dm", 3).await;
    insert_status_stats(&pool, dm, 0, 0).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.iter().all(|c| c.item.text != "secret-dm"),
        "direct messages must never appear in network candidates"
    );
}

#[sqlx::test]
async fn follower_only_posts_excluded_from_candidates(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;

    let public_seed = insert_status(&pool, alice, "public").await;
    insert_favourite(&pool, user, public_seed).await;
    let private = insert_status_with_visibility(&pool, alice, "follower-only", 2).await;
    insert_status_stats(&pool, private, 0, 0).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.iter().all(|c| c.item.text != "follower-only"),
        "follower-only posts must not leak via affinity-based selection"
    );
}

#[sqlx::test]
async fn deleted_statuses_excluded_from_candidates(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;

    let seed = insert_status(&pool, alice, "seed").await;
    insert_favourite(&pool, user, seed).await;
    let deleted = insert_status(&pool, alice, "deleted-post").await;
    insert_status_stats(&pool, deleted, 0, 0).await;
    mark_status_deleted(&pool, deleted).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.iter().all(|c| c.item.text != "deleted-post"),
        "soft-deleted statuses must not surface"
    );
}

#[sqlx::test]
async fn suspended_account_posts_excluded(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;

    let seed = insert_status(&pool, alice, "seed").await;
    insert_favourite(&pool, user, seed).await;
    let post = insert_status(&pool, alice, "post-after-suspension").await;
    insert_status_stats(&pool, post, 0, 0).await;
    mark_account_suspended(&pool, alice).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.is_empty(),
        "suspended accounts must contribute zero candidates"
    );
}

#[sqlx::test]
async fn silenced_account_posts_excluded(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;

    let seed = insert_status(&pool, alice, "seed").await;
    insert_favourite(&pool, user, seed).await;
    let post = insert_status(&pool, alice, "post-after-silence").await;
    insert_status_stats(&pool, post, 0, 0).await;
    mark_account_silenced(&pool, alice).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.is_empty(),
        "silenced accounts must not surface in v1 (no follow verification yet)"
    );
}

#[sqlx::test]
async fn blocked_account_posts_excluded(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;

    let seed = insert_status(&pool, alice, "seed").await;
    insert_favourite(&pool, user, seed).await;
    let post = insert_status(&pool, alice, "post-after-block").await;
    insert_status_stats(&pool, post, 0, 0).await;
    insert_block(&pool, user, alice).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.is_empty(),
        "blocked authors must contribute zero candidates"
    );
}

#[sqlx::test]
async fn muted_account_posts_excluded(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;

    let seed = insert_status(&pool, alice, "seed").await;
    insert_favourite(&pool, user, seed).await;
    let post = insert_status(&pool, alice, "post-after-mute").await;
    insert_status_stats(&pool, post, 0, 0).await;
    insert_mute(&pool, user, alice).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.is_empty(),
        "muted authors must contribute zero candidates"
    );
}

#[sqlx::test]
async fn domain_blocked_posts_excluded(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let bob = insert_account_with_domain(&pool, "bob", "spam.example").await;

    let seed = insert_status(&pool, bob, "seed").await;
    insert_favourite(&pool, user, seed).await;
    let post = insert_status(&pool, bob, "post-from-blocked-domain").await;
    insert_status_stats(&pool, post, 0, 0).await;
    insert_domain_block(&pool, user, "spam.example").await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.is_empty(),
        "accounts on a domain you blocked must contribute zero candidates"
    );
}

#[sqlx::test]
async fn replies_to_others_excluded_self_threads_included(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;
    let bob = insert_account(&pool, "bob").await;

    let seed = insert_status(&pool, alice, "seed").await;
    insert_favourite(&pool, user, seed).await;

    let alice_thread_root = insert_status(&pool, alice, "thread-root").await;
    insert_status_stats(&pool, alice_thread_root, 0, 0).await;

    let alice_self_reply =
        insert_reply(&pool, alice, "self-thread-2", alice_thread_root, alice).await;
    insert_status_stats(&pool, alice_self_reply, 0, 0).await;

    let alice_reply_to_bob =
        insert_reply(&pool, alice, "reply-to-bob", alice_thread_root, bob).await;
    insert_status_stats(&pool, alice_reply_to_bob, 0, 0).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    let texts: Vec<&str> = candidates.iter().map(|c| c.item.text.as_str()).collect();
    assert!(
        texts.contains(&"thread-root"),
        "the original top-level post must appear"
    );
    assert!(
        texts.contains(&"self-thread-2"),
        "self-thread continuations must appear (matches Mastodon's home feed behavior)"
    );
    assert!(
        !texts.contains(&"reply-to-bob"),
        "replies to other users must not appear without conversation context"
    );
}

#[sqlx::test]
async fn reblogs_excluded_from_candidates(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let alice = insert_account(&pool, "alice").await;
    let bob = insert_account(&pool, "bob").await;

    let seed = insert_status(&pool, alice, "seed").await;
    insert_favourite(&pool, user, seed).await;

    let bob_original = insert_status(&pool, bob, "bob-original").await;
    let alice_reblog = insert_reblog(&pool, alice, "alice-reblog", bob_original).await;
    insert_status_stats(&pool, alice_reblog, 0, 0).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    assert!(
        candidates.iter().all(|c| c.item.text != "alice-reblog"),
        "reblogs must not appear as candidates in v1 (will be added with proper dedup later)"
    );
}

#[sqlx::test]
async fn network_engagement_boosts_score(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;
    let user = insert_account(&pool, "viewer").await;
    let author = insert_account(&pool, "author").await;
    let friend = insert_account(&pool, "friend").await;

    insert_follow(&pool, user, friend).await;

    let seed = insert_status(&pool, author, "seed").await;
    insert_favourite(&pool, user, seed).await;

    let liked = insert_status(&pool, author, "liked-by-friend").await;
    let bare = insert_status(&pool, author, "no-network-engagement").await;
    insert_status_stats(&pool, liked, 0, 0).await;
    insert_status_stats(&pool, bare, 0, 0).await;
    insert_favourite(&pool, friend, liked).await;

    let source = NetworkSource::new(pool, user, "local.test".into(), common::test_media());
    let candidates = source.collect(20).await;

    let liked_score = candidates
        .iter()
        .find(|c| c.item.text == "liked-by-friend")
        .map(|c| c.score)
        .expect("liked-by-friend candidate missing");
    let bare_score = candidates
        .iter()
        .find(|c| c.item.text == "no-network-engagement")
        .map(|c| c.score)
        .expect("no-network-engagement candidate missing");

    assert!(
        liked_score > bare_score,
        "post liked by a followed account should outrank an identical bare post (liked={liked_score}, bare={bare_score})"
    );
}
