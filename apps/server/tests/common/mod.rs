use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use serde::Serialize;
use sqlx::PgPool;
use tower::ServiceExt;

use server::state::AppStateInner;

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
        setup_db(&pool).await;

        let state = AppStateInner::new(pool, "nomic_v1.5_64d".into(), "test.example.com".into());
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
}
