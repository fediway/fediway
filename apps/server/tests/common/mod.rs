use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use serde::Serialize;
use sqlx::PgPool;
use tower::ServiceExt;

use server::state::AppStateInner;

pub struct TestApp {
    router: axum::Router,
    pool: PgPool,
    db_name: String,
}

pub struct TestResponse {
    pub status: StatusCode,
    pub body: String,
}

impl TestResponse {
    pub fn json(&self) -> serde_json::Value {
        serde_json::from_str(&self.body).expect("response body is not valid JSON")
    }
}

impl TestApp {
    pub async fn spawn() -> Option<Self> {
        tokio::time::timeout(std::time::Duration::from_secs(15), Self::spawn_inner())
            .await
            .ok()?
    }

    async fn spawn_inner() -> Option<Self> {
        let pool = setup_test_db().await?;
        let db_name = pool
            .connect_options()
            .get_database()
            .unwrap_or("")
            .to_string();

        let state = AppStateInner::new(pool.clone(), "bge_small_64d".into());
        let router = server::routes::router(state, "");

        Some(Self {
            router,
            pool,
            db_name,
        })
    }

    pub fn pool(&self) -> &PgPool {
        &self.pool
    }

    pub async fn get(&self, path: &str) -> TestResponse {
        let response = self
            .router
            .clone()
            .oneshot(Request::get(path).body(Body::empty()).unwrap())
            .await
            .unwrap();

        let status = response.status();
        let bytes = response.into_body().collect().await.unwrap().to_bytes();
        TestResponse {
            status,
            body: String::from_utf8(bytes.to_vec()).unwrap(),
        }
    }

    #[allow(dead_code)]
    pub async fn post_json(&self, path: &str, body: &impl Serialize) -> TestResponse {
        let response = self
            .router
            .clone()
            .oneshot(
                Request::post(path)
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_string(body).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        let status = response.status();
        let bytes = response.into_body().collect().await.unwrap().to_bytes();
        TestResponse {
            status,
            body: String::from_utf8(bytes.to_vec()).unwrap(),
        }
    }
}

impl Drop for TestApp {
    fn drop(&mut self) {
        let db_name = self.db_name.clone();
        let pool = self.pool.clone();
        std::thread::spawn(move || {
            let rt = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .unwrap();
            rt.block_on(async {
                pool.close().await;
                if let Ok(admin) = PgPool::connect(&admin_url()).await {
                    let _ = sqlx::query(&format!("DROP DATABASE IF EXISTS \"{db_name}\""))
                        .execute(&admin)
                        .await;
                }
            });
        })
        .join()
        .ok();
    }
}

fn admin_url() -> String {
    let host = std::env::var("DB_HOST").unwrap_or_else(|_| "localhost".into());
    let port = std::env::var("DB_PORT").unwrap_or_else(|_| "5432".into());
    let user = std::env::var("DB_USER").unwrap_or_else(|_| "fediway".into());
    let pass = std::env::var("DB_PASS").unwrap_or_else(|_| "fediway".into());
    format!("postgres://{user}:{pass}@{host}:{port}/postgres")
}

async fn setup_test_db() -> Option<PgPool> {
    let admin_pool = PgPool::connect(&admin_url()).await.ok()?;
    let db_name = format!("fediway_test_{}", uuid::Uuid::new_v4().simple());
    sqlx::query(&format!("CREATE DATABASE \"{db_name}\""))
        .execute(&admin_pool)
        .await
        .ok()?;

    let host = std::env::var("DB_HOST").unwrap_or_else(|_| "localhost".into());
    let port = std::env::var("DB_PORT").unwrap_or_else(|_| "5432".into());
    let user = std::env::var("DB_USER").unwrap_or_else(|_| "fediway".into());
    let pass = std::env::var("DB_PASS").unwrap_or_else(|_| "fediway".into());
    let url = format!("postgres://{user}:{pass}@{host}:{port}/{db_name}");

    let pool = PgPool::connect(&url).await.ok()?;
    state::db::migrate(&pool).await.ok()?;
    Some(pool)
}
