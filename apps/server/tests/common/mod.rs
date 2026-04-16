#[allow(dead_code)]
pub mod mastodon;

use std::time::Duration;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use serde::Serialize;
use sources::mastodon::MediaConfig;
use sqlx::PgPool;
use state::cache::Cache;
use tower::ServiceExt;

use server::state::AppStateInner;

pub fn test_media() -> MediaConfig {
    MediaConfig::new("local.test".into(), false)
}

pub struct TestApp {
    router: axum::Router,
}

pub struct TestResponse {
    pub status: StatusCode,
    pub body: String,
    headers: axum::http::HeaderMap,
}

impl TestResponse {
    pub fn json(&self) -> serde_json::Value {
        serde_json::from_str(&self.body).expect("response body is not valid JSON")
    }

    pub fn header(&self, name: &str) -> Option<&str> {
        self.headers.get(name).and_then(|v| v.to_str().ok())
    }
}

/// Subset of the Mastodon schema covering only the columns and indexes
/// fediway's local sources query. Mirror real Mastodon when adding more.
pub async fn setup_mastodon_schema(pool: &PgPool) {
    for stmt in [
        r"CREATE TABLE IF NOT EXISTS accounts (
            id                  BIGSERIAL PRIMARY KEY,
            username            TEXT NOT NULL DEFAULT '',
            domain              TEXT,
            display_name        TEXT NOT NULL DEFAULT '',
            note                TEXT NOT NULL DEFAULT '',
            url                 TEXT,
            uri                 TEXT NOT NULL DEFAULT '',
            suspended_at        TIMESTAMP,
            silenced_at         TIMESTAMP,
            memorial            BOOLEAN NOT NULL DEFAULT FALSE,
            moved_to_account_id BIGINT,
            avatar_file_name    TEXT,
            avatar_remote_url   TEXT,
            header_file_name    TEXT,
            header_remote_url   TEXT NOT NULL DEFAULT '',
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            discoverable        BOOLEAN,
            indexable           BOOLEAN NOT NULL DEFAULT FALSE,
            locked              BOOLEAN NOT NULL DEFAULT FALSE,
            actor_type          TEXT,
            fields              JSONB
        )",
        r"CREATE TABLE IF NOT EXISTS account_stats (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            statuses_count      BIGINT NOT NULL DEFAULT 0,
            following_count     BIGINT NOT NULL DEFAULT 0,
            followers_count     BIGINT NOT NULL DEFAULT 0,
            last_status_at      TIMESTAMP,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS statuses (
            id                              BIGSERIAL PRIMARY KEY,
            account_id                      BIGINT NOT NULL,
            uri                             TEXT,
            url                             TEXT,
            text                            TEXT NOT NULL DEFAULT '',
            spoiler_text                    TEXT NOT NULL DEFAULT '',
            sensitive                       BOOLEAN NOT NULL DEFAULT FALSE,
            language                        TEXT,
            visibility                      INTEGER NOT NULL DEFAULT 0,
            reblog_of_id                    BIGINT,
            in_reply_to_id                  BIGINT,
            in_reply_to_account_id          BIGINT,
            ordered_media_attachment_ids    BIGINT[],
            created_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
            edited_at                       TIMESTAMP,
            deleted_at                      TIMESTAMP
        )",
        r"CREATE TABLE IF NOT EXISTS media_attachments (
            id                      BIGSERIAL PRIMARY KEY,
            status_id               BIGINT,
            account_id              BIGINT,
            type                    INTEGER NOT NULL DEFAULT 0,
            description             TEXT,
            remote_url              TEXT NOT NULL DEFAULT '',
            blurhash                TEXT,
            file_file_name          TEXT,
            file_meta               JSON,
            thumbnail_file_name     TEXT,
            created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS preview_cards (
            id                  BIGSERIAL PRIMARY KEY,
            url                 TEXT NOT NULL DEFAULT '',
            title               TEXT NOT NULL DEFAULT '',
            description         TEXT NOT NULL DEFAULT '',
            type                INTEGER NOT NULL DEFAULT 0,
            html                TEXT NOT NULL DEFAULT '',
            author_name         TEXT NOT NULL DEFAULT '',
            author_url          TEXT NOT NULL DEFAULT '',
            provider_name       TEXT NOT NULL DEFAULT '',
            provider_url        TEXT NOT NULL DEFAULT '',
            image_file_name     TEXT,
            image_description   TEXT NOT NULL DEFAULT '',
            width               INTEGER NOT NULL DEFAULT 0,
            height              INTEGER NOT NULL DEFAULT 0,
            embed_url           TEXT NOT NULL DEFAULT '',
            blurhash            TEXT,
            language            TEXT,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS preview_cards_statuses (
            preview_card_id     BIGINT NOT NULL,
            status_id           BIGINT NOT NULL,
            PRIMARY KEY (preview_card_id, status_id)
        )",
        r"CREATE TABLE IF NOT EXISTS custom_emojis (
            id                      BIGSERIAL PRIMARY KEY,
            shortcode               TEXT NOT NULL,
            domain                  TEXT,
            image_file_name         TEXT,
            image_remote_url        TEXT,
            disabled                BOOLEAN NOT NULL DEFAULT FALSE,
            visible_in_picker       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS quotes (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            status_id           BIGINT NOT NULL,
            quoted_account_id   BIGINT,
            quoted_status_id    BIGINT,
            state               INTEGER NOT NULL DEFAULT 0,
            legacy              BOOLEAN NOT NULL DEFAULT FALSE,
            activity_uri        TEXT,
            approval_uri        TEXT,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS tags (
            id              BIGSERIAL PRIMARY KEY,
            name            TEXT NOT NULL UNIQUE
        )",
        r"CREATE TABLE IF NOT EXISTS statuses_tags (
            status_id       BIGINT NOT NULL,
            tag_id          BIGINT NOT NULL,
            PRIMARY KEY (tag_id, status_id)
        )",
        r"CREATE TABLE IF NOT EXISTS status_stats (
            id                  BIGSERIAL PRIMARY KEY,
            status_id           BIGINT NOT NULL,
            replies_count       BIGINT NOT NULL DEFAULT 0,
            reblogs_count       BIGINT NOT NULL DEFAULT 0,
            favourites_count    BIGINT NOT NULL DEFAULT 0,
            quotes_count        BIGINT NOT NULL DEFAULT 0,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS favourites (
            id              BIGSERIAL PRIMARY KEY,
            account_id      BIGINT NOT NULL,
            status_id       BIGINT NOT NULL,
            created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS bookmarks (
            id              BIGSERIAL PRIMARY KEY,
            account_id      BIGINT NOT NULL,
            status_id       BIGINT NOT NULL,
            created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS mentions (
            id              BIGSERIAL PRIMARY KEY,
            status_id       BIGINT NOT NULL,
            account_id      BIGINT NOT NULL,
            silent          BOOLEAN NOT NULL DEFAULT FALSE,
            created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS follows (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            target_account_id   BIGINT NOT NULL,
            show_reblogs        BOOLEAN NOT NULL DEFAULT TRUE,
            notify              BOOLEAN NOT NULL DEFAULT FALSE,
            uri                 TEXT,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS blocks (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            target_account_id   BIGINT NOT NULL,
            uri                 TEXT,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS mutes (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            target_account_id   BIGINT NOT NULL,
            hide_notifications  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS account_domain_blocks (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            domain              TEXT NOT NULL,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_status_stats_on_status_id
            ON status_stats (status_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_favourites_on_account_id_and_status_id
            ON favourites (account_id, status_id)",
        r"CREATE INDEX IF NOT EXISTS index_favourites_on_status_id
            ON favourites (status_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_bookmarks_on_account_id_and_status_id
            ON bookmarks (account_id, status_id)",
        r"CREATE INDEX IF NOT EXISTS index_bookmarks_on_status_id
            ON bookmarks (status_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_mentions_on_account_id_and_status_id
            ON mentions (account_id, status_id)",
        r"CREATE INDEX IF NOT EXISTS index_mentions_on_status_id
            ON mentions (status_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_follows_on_account_id_and_target_account_id
            ON follows (account_id, target_account_id)",
        r"CREATE INDEX IF NOT EXISTS index_follows_on_target_account_id_and_account_id
            ON follows (target_account_id, account_id)",
        r"CREATE INDEX IF NOT EXISTS index_statuses_on_account_id
            ON statuses (account_id)",
        r"CREATE INDEX IF NOT EXISTS index_statuses_on_reblog_of_id_and_account_id
            ON statuses (reblog_of_id, account_id)",
        r"CREATE INDEX IF NOT EXISTS index_statuses_on_in_reply_to_account_id
            ON statuses (in_reply_to_account_id) WHERE in_reply_to_account_id IS NOT NULL",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_blocks_on_account_id_and_target_account_id
            ON blocks (account_id, target_account_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_mutes_on_account_id_and_target_account_id
            ON mutes (account_id, target_account_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_account_domain_blocks_on_account_id_and_domain
            ON account_domain_blocks (account_id, domain)",
        r"CREATE INDEX IF NOT EXISTS index_media_attachments_on_status_id
            ON media_attachments (status_id) WHERE status_id IS NOT NULL",
        r"CREATE INDEX IF NOT EXISTS index_preview_cards_statuses_on_status_id
            ON preview_cards_statuses (status_id)",
        r"CREATE INDEX IF NOT EXISTS index_custom_emojis_on_shortcode_and_domain
            ON custom_emojis (shortcode, domain)",
    ] {
        sqlx::query(stmt)
            .execute(pool)
            .await
            .expect("failed to create mastodon schema");
    }
}

/// Mock Mastodon's `timestamp_id()` function and run migrations.
/// Call this at the start of any test that touches the database.
pub async fn setup_db(pool: &PgPool) {
    sqlx::query(
        r"DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'timestamp_id') THEN
                CREATE FUNCTION timestamp_id(table_name text) RETURNS bigint AS $fn$
                DECLARE
                    time_part bigint;
                    tail bigint;
                BEGIN
                    time_part := (date_part('epoch', now()) * 1000)::bigint << 16;
                    tail := nextval(table_name || '_id_seq') & 65535;
                    RETURN time_part | tail;
                END;
                $fn$ LANGUAGE plpgsql VOLATILE;
            END IF;
        END
        $$",
    )
    .execute(pool)
    .await
    .expect("failed to create timestamp_id stub");

    state::db::migrate(pool).await.expect("migrations failed");
}

impl TestApp {
    pub async fn from_pool(pool: PgPool) -> Self {
        Self::from_pool_with_mastodon(pool, None).await
    }

    pub async fn from_pool_with_mastodon(pool: PgPool, mastodon_api_url: Option<String>) -> Self {
        setup_db(&pool).await;
        setup_mastodon_fixture(&pool).await;

        let cache = Cache::disabled();
        let media = MediaConfig::new("example.com".into(), false);
        let state = AppStateInner::new(
            pool,
            cache,
            media,
            "nomic_v1.5_64d".into(),
            "example.com".into(),
            mastodon_api_url,
        );
        let router = server::routes::router(state);
        Self { router }
    }

    pub async fn get(&self, path: &str) -> TestResponse {
        self.raw_request(Request::get(path).body(Body::empty()).unwrap())
            .await
    }

    pub async fn raw_request(&self, request: Request<Body>) -> TestResponse {
        let response = tokio::time::timeout(
            std::time::Duration::from_secs(15),
            self.router.clone().oneshot(request),
        )
        .await
        .expect("request timed out after 15s")
        .unwrap();

        let status = response.status();
        let headers = response.headers().clone();
        let bytes = response.into_body().collect().await.unwrap().to_bytes();
        TestResponse {
            status,
            body: String::from_utf8(bytes.to_vec()).unwrap(),
            headers,
        }
    }

    #[allow(dead_code)]
    pub async fn post_json(&self, path: &str, body: &impl Serialize) -> TestResponse {
        self.raw_request(
            Request::post(path)
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(body).unwrap()))
                .unwrap(),
        )
        .await
    }

    #[allow(dead_code)]
    pub async fn get_with_token(&self, path: &str, token: &str) -> TestResponse {
        self.raw_request(
            Request::get(path)
                .header("authorization", format!("Bearer {token}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
    }
}

/// Minimal Mastodon-compatible schema for auth tests.
///
/// Mirrors only the columns `apps/server/src/auth.rs` actually reads. No FKs
/// to upstream tables, no extra columns, no `timestamp_id` defaults — just
/// enough to exercise the token resolver and its user-state guards.
const MASTODON_FIXTURE_DDL: &str = "
CREATE TABLE IF NOT EXISTS accounts (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR NOT NULL DEFAULT '',
    suspended_at TIMESTAMP,
    memorial BOOLEAN NOT NULL DEFAULT FALSE,
    moved_to_account_id BIGINT
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    confirmed_at TIMESTAMP,
    approved BOOLEAN NOT NULL DEFAULT TRUE,
    disabled BOOLEAN NOT NULL DEFAULT FALSE,
    chosen_languages VARCHAR[],
    locale VARCHAR
);

CREATE TABLE IF NOT EXISTS oauth_access_tokens (
    id BIGSERIAL PRIMARY KEY,
    token VARCHAR NOT NULL UNIQUE,
    refresh_token VARCHAR,
    expires_in INTEGER,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    scopes VARCHAR,
    application_id BIGINT,
    resource_owner_id BIGINT,
    last_used_at TIMESTAMP,
    last_used_ip INET
);
";

/// Create the minimal Mastodon-compatible tables `auth.rs` queries.
/// Call this in any test that needs a working bearer-token flow.
#[allow(dead_code)]
pub async fn setup_mastodon_fixture(pool: &PgPool) {
    sqlx::raw_sql(MASTODON_FIXTURE_DDL)
        .execute(pool)
        .await
        .expect("failed to create mastodon test fixture");
}

/// A test user with a valid OAuth bearer token. Construct via [`TestUser::builder`].
#[allow(dead_code)]
pub struct TestUser {
    pub user_id: i64,
    pub account_id: i64,
    pub username: String,
    pub token: String,
}

impl TestUser {
    #[allow(dead_code)]
    pub fn builder() -> TestUserBuilder {
        TestUserBuilder::default()
    }
}

/// Builder for a Mastodon-shaped test user. Defaults to a fully-functional user
/// (confirmed, approved, not disabled) with a valid, non-revoked token. Override
/// any field to test the corresponding rejection path.
// Each bool is an independent toggle, not state — a state machine would make
// the test API strictly worse, so we opt out of the pedantic lint here.
#[allow(dead_code, clippy::struct_excessive_bools)]
pub struct TestUserBuilder {
    confirmed: bool,
    approved: bool,
    disabled: bool,
    suspended: bool,
    memorial: bool,
    moved: bool,
    revoked: bool,
}

impl Default for TestUserBuilder {
    fn default() -> Self {
        Self {
            confirmed: true,
            approved: true,
            disabled: false,
            suspended: false,
            memorial: false,
            moved: false,
            revoked: false,
        }
    }
}

#[allow(dead_code)]
impl TestUserBuilder {
    #[must_use]
    pub fn unconfirmed(mut self) -> Self {
        self.confirmed = false;
        self
    }

    #[must_use]
    pub fn unapproved(mut self) -> Self {
        self.approved = false;
        self
    }

    #[must_use]
    pub fn disabled(mut self) -> Self {
        self.disabled = true;
        self
    }

    #[must_use]
    pub fn suspended(mut self) -> Self {
        self.suspended = true;
        self
    }

    #[must_use]
    pub fn memorial(mut self) -> Self {
        self.memorial = true;
        self
    }

    #[must_use]
    pub fn moved(mut self) -> Self {
        self.moved = true;
        self
    }

    #[must_use]
    pub fn revoked(mut self) -> Self {
        self.revoked = true;
        self
    }

    pub async fn insert(self, pool: &PgPool) -> TestUser {
        // Process-nanos suffix keeps usernames + tokens unique within a single test.
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("system time before epoch")
            .as_nanos();
        let username = format!("u{nanos:x}");
        let token = format!("tok_{nanos:x}");
        // Sentinel value for the "moved" case — auth only cares NULL vs non-NULL.
        let moved_to: Option<i64> = if self.moved { Some(999_999) } else { None };

        let account_id: i64 = sqlx::query_scalar(
            "INSERT INTO accounts (username, suspended_at, memorial, moved_to_account_id)
             VALUES ($1, CASE WHEN $2 THEN NOW() END, $3, $4)
             RETURNING id",
        )
        .bind(&username)
        .bind(self.suspended)
        .bind(self.memorial)
        .bind(moved_to)
        .fetch_one(pool)
        .await
        .expect("insert account");

        let user_id: i64 = sqlx::query_scalar(
            "INSERT INTO users (account_id, confirmed_at, approved, disabled)
             VALUES ($1, CASE WHEN $2 THEN NOW() END, $3, $4)
             RETURNING id",
        )
        .bind(account_id)
        .bind(self.confirmed)
        .bind(self.approved)
        .bind(self.disabled)
        .fetch_one(pool)
        .await
        .expect("insert user");

        sqlx::query(
            "INSERT INTO oauth_access_tokens (token, resource_owner_id, revoked_at, created_at, scopes)
             VALUES ($1, $2, CASE WHEN $3 THEN NOW() END, NOW(), 'read write follow')",
        )
        .bind(&token)
        .bind(user_id)
        .bind(self.revoked)
        .execute(pool)
        .await
        .expect("insert oauth token");

        TestUser {
            user_id,
            account_id,
            username,
            token,
        }
    }
}
