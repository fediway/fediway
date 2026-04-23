#[allow(dead_code)]
pub mod mastodon;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use serde::Serialize;
use sources::mastodon::MediaConfig;
use sqlx::PgPool;
use state::cache::Cache;
use tower::ServiceExt;

use server::state::AppStateInner;

#[allow(unused_imports)]
pub use test_support::media::{test_media, test_media_s3};
#[allow(unused_imports)]
pub use test_support::schema::{setup_mastodon_fixture, setup_mastodon_schema};
#[allow(unused_imports)]
pub use test_support::users::{TestUser, TestUserBuilder};

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

pub async fn setup_db(pool: &PgPool) {
    test_support::schema::install_timestamp_id(pool).await;
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
