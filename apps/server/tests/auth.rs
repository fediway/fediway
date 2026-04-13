mod common;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use sqlx::PgPool;

const HOME: &str = "/api/v1/timelines/home";

// ─── Token extraction ────────────────────────────────────────────────────────

#[sqlx::test]
async fn missing_authorization_header_returns_401(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get(HOME).await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn wrong_auth_scheme_returns_401(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let req = Request::get(HOME)
        .header("authorization", "Basic dXNlcjpwYXNz")
        .body(Body::empty())
        .unwrap();
    let resp = app.raw_request(req).await;

    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn empty_bearer_token_returns_401(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, "").await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

// ─── Token resolution ────────────────────────────────────────────────────────

#[sqlx::test]
async fn unknown_token_returns_401(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app
        .get_with_token(HOME, "definitely-not-a-real-token")
        .await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn valid_token_is_accepted(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().insert(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, &user.token).await;
    assert_eq!(
        resp.status,
        StatusCode::OK,
        "valid bearer token should resolve to an Account; body: {}",
        resp.body
    );
}

#[sqlx::test]
async fn revoked_token_is_rejected(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().revoked().insert(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, &user.token).await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn expired_token_is_rejected(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().insert(&pool).await;
    // Backdate creation by an hour and set a 60s expiration → token is 59 minutes expired.
    sqlx::query(
        "UPDATE oauth_access_tokens
         SET created_at = NOW() - INTERVAL '1 hour', expires_in = 60
         WHERE token = $1",
    )
    .bind(&user.token)
    .execute(&pool)
    .await
    .expect("backdate token");
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, &user.token).await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn application_only_token_is_rejected(pool: PgPool) {
    // Doorkeeper's client_credentials grant issues tokens with a NULL resource_owner_id.
    // The JOIN on users excludes them → no Account, 401.
    common::setup_mastodon_fixture(&pool).await;
    sqlx::query(
        "INSERT INTO oauth_access_tokens (token, resource_owner_id, created_at, scopes)
         VALUES ('app_only_token', NULL, NOW(), 'read')",
    )
    .execute(&pool)
    .await
    .expect("insert app-only token");
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, "app_only_token").await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

// ─── User-state guards (mirror Mastodon Api::BaseController#require_user!) ──

#[sqlx::test]
async fn unconfirmed_user_is_rejected(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder()
        .unconfirmed()
        .insert(&pool)
        .await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, &user.token).await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn unapproved_user_is_rejected(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().unapproved().insert(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, &user.token).await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn disabled_user_is_rejected(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().disabled().insert(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, &user.token).await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn suspended_account_is_rejected(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().suspended().insert(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, &user.token).await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn memorial_account_is_rejected(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().memorial().insert(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, &user.token).await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}

#[sqlx::test]
async fn moved_account_is_rejected(pool: PgPool) {
    common::setup_mastodon_fixture(&pool).await;
    let user = common::TestUser::builder().moved().insert(&pool).await;
    let app = common::TestApp::from_pool(pool).await;

    let resp = app.get_with_token(HOME, &user.token).await;
    assert_eq!(resp.status, StatusCode::UNAUTHORIZED);
}
