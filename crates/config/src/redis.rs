use std::env;

use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct RedisConfig {
    #[serde(default = "default_host")]
    pub redis_host: String,
    #[serde(default = "default_port")]
    pub redis_port: u16,
}

impl RedisConfig {
    #[must_use]
    pub fn load() -> Self {
        Self {
            redis_host: env::var("REDIS_HOST").unwrap_or_else(|_| "localhost".to_string()),
            redis_port: env::var("REDIS_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(6379),
        }
    }
}

fn default_host() -> String {
    "localhost".to_string()
}
fn default_port() -> u16 {
    6379
}
