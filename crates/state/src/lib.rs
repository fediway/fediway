pub mod cache;
pub mod db;
pub mod feed_store;
pub mod orbit;
pub mod policy;
pub mod providers;
pub mod redis;
pub mod statuses;

use ::redis::aio::ConnectionManager;
use config::{DatabaseConfig, RedisConfig};
use sqlx::PgPool;

#[derive(Clone)]
pub struct AppState {
    pub db: PgPool,
    pub redis: ConnectionManager,
}

impl AppState {
    pub async fn from_config(
        db_config: &DatabaseConfig,
        redis_config: &RedisConfig,
    ) -> Result<Self, AppStateError> {
        let db = db::connect(db_config)
            .await
            .map_err(AppStateError::Database)?;
        let redis = redis::connect(redis_config)
            .await
            .map_err(AppStateError::Redis)?;
        Ok(Self { db, redis })
    }
}

#[derive(Debug, thiserror::Error)]
pub enum AppStateError {
    #[error("database: {0}")]
    Database(sqlx::Error),

    #[error("redis: {0}")]
    Redis(::redis::RedisError),
}
