use std::path::PathBuf;
use std::sync::LazyLock;
use std::sync::atomic::{AtomicI64, Ordering};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use reqwest::header::{HeaderMap, HeaderValue};
use serde::Deserialize;
use serde_json::json;
use sqlx::PgPool;

use server::auth::BearerToken;

pub const MASTODON_BASE: &str = "http://localhost:3000";

/// Subset of Mastodon's `Status` entity relevant to integration tests.
///
/// Kept deliberately non-`#[serde(default)]` so that a field rename or
/// removal in a future Mastodon version fails loudly during deserialization
/// instead of silently nulling out counters we assert against.
#[derive(Debug, Deserialize)]
pub struct MastodonStatus {
    pub id: String,
    pub uri: String,
    pub url: Option<String>,
    pub favourited: bool,
    pub favourites_count: u64,
    pub reblogged: bool,
    pub reblogs_count: u64,
    pub bookmarked: bool,
    pub replies_count: u64,
    pub in_reply_to_id: Option<String>,
    pub reblog: Option<Box<MastodonStatus>>,
}

#[derive(Debug, Deserialize)]
pub struct MastodonReport {
    pub id: String,
    pub action_taken: bool,
    pub comment: String,
    pub status_ids: Vec<String>,
}

pub fn load_token() -> BearerToken {
    if let Ok(env) = std::env::var("MASTODON_TEST_TOKEN") {
        return BearerToken::new(env);
    }
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../docker/mastodon-token/mastodon_token");
    let raw = std::fs::read_to_string(&path).unwrap_or_else(|_| {
        panic!(
            "missing {}. Run `docker compose -f docker-compose.integration.yaml up -d` from repos/fediway first",
            path.display()
        )
    });
    BearerToken::new(raw.trim().to_string())
}

pub fn http_client() -> reqwest::Client {
    // Rails' `force_ssl` rejects plain-HTTP requests in production mode unless
    // the caller sends `X-Forwarded-Proto: https` from a trusted proxy. Rails
    // trusts private-IP ranges by default, so sending this header from
    // localhost is enough — no Mastodon env tweaks needed.
    let mut headers = HeaderMap::new();
    headers.insert("x-forwarded-proto", HeaderValue::from_static("https"));
    reqwest::Client::builder()
        .timeout(Duration::from_secs(15))
        .connect_timeout(Duration::from_secs(3))
        .redirect(reqwest::redirect::Policy::none())
        .default_headers(headers)
        .build()
        .unwrap()
}

pub async fn create_status(
    http: &reqwest::Client,
    token: &BearerToken,
    text: &str,
) -> MastodonStatus {
    let resp = http
        .post(format!("{MASTODON_BASE}/api/v1/statuses"))
        .bearer_auth(token.as_str())
        .json(&json!({ "status": text, "visibility": "public" }))
        .send()
        .await
        .expect("POST /api/v1/statuses");
    assert!(
        resp.status().is_success(),
        "POST /api/v1/statuses returned {}",
        resp.status()
    );
    resp.json().await.expect("deserialize MastodonStatus")
}

pub async fn fetch_status(http: &reqwest::Client, token: &BearerToken, id: &str) -> MastodonStatus {
    let resp = http
        .get(format!("{MASTODON_BASE}/api/v1/statuses/{id}"))
        .bearer_auth(token.as_str())
        .send()
        .await
        .expect("GET /api/v1/statuses/:id");
    assert!(
        resp.status().is_success(),
        "GET /api/v1/statuses/{id} returned {}",
        resp.status()
    );
    resp.json().await.expect("deserialize MastodonStatus")
}

/// Seeds the local test database with `accounts`/`users`/`oauth_access_tokens`
/// rows so that the `Account` extractor accepts `token` against the TestApp
/// pool, while the same token still validates against the real Mastodon
/// instance when handlers forward it. Both sides of the dual-DB test setup
/// agree on the same bearer string.
pub async fn seed_local_auth(pool: &PgPool, token: &BearerToken) {
    super::setup_mastodon_fixture(pool).await;

    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let username = format!("integ_u{nanos:x}");

    let account_id: i64 =
        sqlx::query_scalar("INSERT INTO accounts (username) VALUES ($1) RETURNING id")
            .bind(&username)
            .fetch_one(pool)
            .await
            .expect("insert account");

    let user_id: i64 = sqlx::query_scalar(
        "INSERT INTO users (account_id, confirmed_at, approved, disabled)
         VALUES ($1, NOW(), TRUE, FALSE) RETURNING id",
    )
    .bind(account_id)
    .fetch_one(pool)
    .await
    .expect("insert user");

    sqlx::query(
        "INSERT INTO oauth_access_tokens (token, resource_owner_id, created_at, scopes)
         VALUES ($1, $2, NOW(), 'read write follow push')",
    )
    .bind(token.as_str())
    .bind(user_id)
    .execute(pool)
    .await
    .expect("insert oauth token");
}

/// Monotonic counter seeded from wall-clock nanoseconds at first use.
/// Guarantees each `seed_commonfeed` call gets a distinct `remote_id` so
/// the `UNIQUE(provider_domain, remote_id)` constraint on
/// `commonfeed_statuses` doesn't upsert two different posts into the same
/// snowflake — a bug that silently corrupts any test that seeds more than
/// one status.
static REMOTE_ID_COUNTER: LazyLock<AtomicI64> = LazyLock::new(|| {
    let seed = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system time before epoch")
        .as_nanos() as i64;
    AtomicI64::new(seed)
});

pub async fn seed_commonfeed(pool: &PgPool, post_uri: &str) -> i64 {
    let remote_id = REMOTE_ID_COUNTER.fetch_add(1, Ordering::SeqCst);
    let post = json!({
        "url": post_uri,
        "content": "<p>integration</p>",
        "text": "integration",
        "author": {
            "handle": "@test@localhost",
            "display_name": "test",
            "url": "https://localhost/@test",
            "emojis": []
        },
        "published_at": "2026-04-15T12:00:00Z",
        "sensitive": false,
        "media": [],
        "engagement": { "replies": 0, "reposts": 0, "likes": 0 },
        "tags": [],
        "emojis": []
    });
    state::statuses::map_post(
        pool,
        "integration.test",
        remote_id,
        post_uri,
        post_uri,
        &post,
    )
    .await
    .expect("map_post failed")
}
