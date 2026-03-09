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
                .unwrap_or(5),
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
    5
}
