mod common;

use std::time::Duration;

use axum::Router;
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::routing::get;
use serde_json::json;
use sqlx::PgPool;

use server::auth::BearerToken;
use server::mastodon::resolve::{ResolveError, Resolver};
use server::mastodon::translate::{translate_request_id, translate_response};

fn sample_post_json(url: &str, handle: &str) -> serde_json::Value {
    json!({
        "url": url,
        "content": "<p>hello</p>",
        "text": "hello",
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

async fn seed_with_mapping(
    pool: &PgPool,
    post_uri: &str,
    provider: &str,
    remote_id: i64,
    mastodon_id: i64,
) -> i64 {
    let post = sample_post_json(post_uri, "@a@example.com");
    let snowflake = state::statuses::map_post(pool, provider, remote_id, post_uri, post_uri, &post)
        .await
        .unwrap();
    state::statuses::set_mastodon_local_id(pool, snowflake, mastodon_id)
        .await
        .unwrap();
    snowflake
}

#[sqlx::test]
async fn translate_response_rewrites_top_level_id(pool: PgPool) {
    common::setup_db(&pool).await;
    let snowflake = seed_with_mapping(&pool, "https://example.com/1", "p", 1, 42).await;

    let mut value = json!({ "id": "42", "content": "x" });
    translate_response(&pool, &mut value).await.unwrap();

    assert_eq!(value["id"], snowflake.to_string());
}

#[sqlx::test]
async fn translate_response_rewrites_in_reply_to_id(pool: PgPool) {
    common::setup_db(&pool).await;
    let parent_snowflake =
        seed_with_mapping(&pool, "https://example.com/parent", "p", 1, 777).await;

    let mut value = json!({
        "id": "999",
        "in_reply_to_id": "777"
    });

    translate_response(&pool, &mut value).await.unwrap();

    assert_eq!(value["id"], "999");
    assert_eq!(value["in_reply_to_id"], parent_snowflake.to_string());
}

#[sqlx::test]
async fn translate_response_rewrites_reblog_ids(pool: PgPool) {
    common::setup_db(&pool).await;
    let inner_snowflake = seed_with_mapping(&pool, "https://example.com/inner", "p", 1, 111).await;
    let parent_snowflake =
        seed_with_mapping(&pool, "https://example.com/parent", "p", 2, 222).await;

    let mut value = json!({
        "id": "900",
        "reblog": {
            "id": "111",
            "in_reply_to_id": "222"
        }
    });

    translate_response(&pool, &mut value).await.unwrap();

    assert_eq!(value["id"], "900");
    assert_eq!(value["reblog"]["id"], inner_snowflake.to_string());
    assert_eq!(
        value["reblog"]["in_reply_to_id"],
        parent_snowflake.to_string()
    );
}

#[sqlx::test]
async fn translate_response_leaves_unmapped_ids_alone(pool: PgPool) {
    common::setup_db(&pool).await;

    let mut value = json!({
        "id": "42",
        "in_reply_to_id": "12345"
    });

    translate_response(&pool, &mut value).await.unwrap();

    assert_eq!(value["id"], "42");
    assert_eq!(value["in_reply_to_id"], "12345");
}

#[sqlx::test]
async fn translate_response_ignores_non_numeric_ids(pool: PgPool) {
    common::setup_db(&pool).await;

    let mut value = json!({
        "id": "not-a-number",
        "in_reply_to_id": "also-not"
    });

    translate_response(&pool, &mut value).await.unwrap();

    assert_eq!(value["id"], "not-a-number");
    assert_eq!(value["in_reply_to_id"], "also-not");
}

#[sqlx::test]
async fn translate_response_handles_null_reblog(pool: PgPool) {
    common::setup_db(&pool).await;

    let mut value = json!({
        "id": "42",
        "reblog": null
    });

    translate_response(&pool, &mut value).await.unwrap();

    assert_eq!(value["id"], "42");
    assert!(value["reblog"].is_null());
}

fn http_client() -> reqwest::Client {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .connect_timeout(Duration::from_secs(2))
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .unwrap()
}

async fn serve(router: Router) -> String {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, router).await.unwrap();
    });
    format!("http://127.0.0.1:{port}")
}

fn search_response(id: &str) -> axum::response::Response {
    axum::Json(json!({
        "accounts": [],
        "hashtags": [],
        "statuses": [{ "id": id }]
    }))
    .into_response()
}

#[sqlx::test]
async fn translate_request_id_rewrites_snowflake_to_mastodon_id(pool: PgPool) {
    common::setup_db(&pool).await;
    let post = sample_post_json("https://example.com/1", "@a@example.com");
    let snowflake = state::statuses::map_post(
        &pool,
        "p",
        1,
        "https://example.com/1",
        "https://example.com/1",
        &post,
    )
    .await
    .unwrap();

    let router = Router::new().route("/api/v2/search", get(|| async { search_response("8888") }));
    let base = serve(router).await;
    let resolver = Resolver::new(pool, http_client(), Some(base));
    let token = BearerToken::new("tok".into());

    let mut id = snowflake.to_string();
    translate_request_id(&resolver, &token, &mut id)
        .await
        .unwrap();

    assert_eq!(id, "8888");
}

#[sqlx::test]
async fn translate_request_id_leaves_native_mastodon_id_alone(pool: PgPool) {
    common::setup_db(&pool).await;
    let router = Router::new().route("/api/v2/search", get(|| async { StatusCode::NOT_FOUND }));
    let base = serve(router).await;
    let resolver = Resolver::new(pool, http_client(), Some(base));
    let token = BearerToken::new("tok".into());

    let mut id = "999999999999".to_string();
    translate_request_id(&resolver, &token, &mut id)
        .await
        .unwrap();

    assert_eq!(id, "999999999999");
}

#[sqlx::test]
async fn translate_request_id_leaves_non_numeric_alone(pool: PgPool) {
    common::setup_db(&pool).await;
    let resolver = Resolver::new(pool, http_client(), Some("http://unused".into()));
    let token = BearerToken::new("tok".into());

    let mut id = "abc-xyz".to_string();
    translate_request_id(&resolver, &token, &mut id)
        .await
        .unwrap();

    assert_eq!(id, "abc-xyz");
}

#[sqlx::test]
async fn translate_request_id_propagates_non_not_found_errors(pool: PgPool) {
    common::setup_db(&pool).await;
    let post = sample_post_json("https://blocked.example/1", "@a@example.com");
    let snowflake = state::statuses::map_post(
        &pool,
        "p",
        1,
        "https://blocked.example/1",
        "https://blocked.example/1",
        &post,
    )
    .await
    .unwrap();

    let router = Router::new().route(
        "/api/v2/search",
        get(|| async { (StatusCode::UNPROCESSABLE_ENTITY, "blocked").into_response() }),
    );
    let base = serve(router).await;
    let resolver = Resolver::new(pool, http_client(), Some(base));
    let token = BearerToken::new("tok".into());

    let mut id = snowflake.to_string();
    let err = translate_request_id(&resolver, &token, &mut id)
        .await
        .unwrap_err();
    assert_eq!(err, ResolveError::Blocked);
}
