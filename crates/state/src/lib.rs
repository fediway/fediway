pub mod db;
pub mod providers;
pub mod redis;

use ::redis::aio::ConnectionManager;
use config::FediwayConfig;
use sqlx::PgPool;

#[derive(Clone)]
pub struct AppState {
    pub db: PgPool,
    pub redis: ConnectionManager,
}

impl AppState {
    pub async fn from_config(config: &FediwayConfig) -> Result<Self, AppStateError> {
        let db = db::connect(&config.db)
            .await
            .map_err(AppStateError::Database)?;
        let redis = redis::connect(&config.redis)
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
