use std::env;

use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct DatabaseConfig {
    #[serde(default = "default_host")]
    pub db_host: String,
    #[serde(default = "default_port")]
    pub db_port: u16,
    #[serde(default = "default_name")]
    pub db_name: String,
    #[serde(default = "default_user")]
    pub db_user: String,
    #[serde(default)]
    pub db_pass: Option<String>,
    #[serde(default = "default_pool_size")]
    pub db_pool_size: u32,
    #[serde(default = "default_pool_min")]
    pub db_pool_min: u32,
    #[serde(default = "default_acquire_timeout")]
    pub db_acquire_timeout_secs: u64,
    #[serde(default = "default_idle_timeout")]
    pub db_idle_timeout_secs: u64,
    #[serde(default = "default_max_lifetime")]
    pub db_max_lifetime_secs: u64,
}

impl DatabaseConfig {
    #[must_use]
    pub fn load() -> Self {
        Self {
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
                .unwrap_or(10),
            db_pool_min: env::var("DB_POOL_MIN")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(2),
            db_acquire_timeout_secs: env::var("DB_ACQUIRE_TIMEOUT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(3),
            db_idle_timeout_secs: env::var("DB_IDLE_TIMEOUT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(600),
            db_max_lifetime_secs: env::var("DB_MAX_LIFETIME")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(1800),
        }
    }
}

fn default_host() -> String {
    "localhost".to_string()
}
fn default_port() -> u16 {
    5432
}
fn default_name() -> String {
    "mastodon_development".to_string()
}
fn default_user() -> String {
    "mastodon".to_string()
}
fn default_pool_size() -> u32 {
    10
}
fn default_pool_min() -> u32 {
    2
}
fn default_acquire_timeout() -> u64 {
    3
}
fn default_idle_timeout() -> u64 {
    600
}
fn default_max_lifetime() -> u64 {
    1800
}
