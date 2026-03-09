mod db;
mod instance;
mod redis;

pub use self::redis::RedisConfig;
pub use db::DatabaseConfig;
pub use instance::InstanceConfig;

use std::env;

#[derive(Debug)]
pub struct FediwayConfig {
    pub db: DatabaseConfig,
    pub redis: RedisConfig,
    pub instance: InstanceConfig,
}

impl FediwayConfig {
    #[must_use]
    pub fn load() -> Self {
        Self {
            db: DatabaseConfig {
                db_host: env::var("DB_HOST").unwrap_or_else(|_| "localhost".to_string()),
                db_port: env::var("DB_PORT")
                    .ok()
                    .and_then(|v| v.parse().ok())
                    .unwrap_or(5432),
                db_name: env::var("DB_NAME").unwrap_or_else(|_| "mastodon_development".to_string()),
                db_user: env::var("DB_USER").unwrap_or_else(|_| "mastodon".to_string()),
                db_pass: env::var("DB_PASS").ok(),
                db_pool_size: env::var("DB_POOL_SIZE")
                    .ok()
                    .and_then(|v| v.parse().ok())
                    .unwrap_or(5),
            },
            redis: RedisConfig {
                redis_host: env::var("REDIS_HOST").unwrap_or_else(|_| "localhost".to_string()),
                redis_port: env::var("REDIS_PORT")
                    .ok()
                    .and_then(|v| v.parse().ok())
                    .unwrap_or(6379),
            },
            instance: InstanceConfig {
                instance_domain: env::var("INSTANCE_DOMAIN").unwrap_or_default(),
                instance_name: env::var("INSTANCE_NAME").unwrap_or_default(),
            },
        }
    }
}

#[cfg(test)]
mod tests;
