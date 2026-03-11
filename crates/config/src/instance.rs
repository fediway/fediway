use std::env;

use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct InstanceConfig {
    pub instance_domain: String,
    pub instance_name: String,
    pub server_host: String,
    pub server_port: u16,
    pub metrics_port: Option<u16>,
}

impl InstanceConfig {
    #[must_use]
    pub fn load() -> Self {
        Self {
            instance_domain: env::var("INSTANCE_DOMAIN").unwrap_or_default(),
            instance_name: env::var("INSTANCE_NAME").unwrap_or_default(),
            server_host: env::var("SERVER_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            server_port: env::var("SERVER_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(3000),
            metrics_port: env::var("METRICS_PORT").ok().and_then(|v| v.parse().ok()),
        }
    }
}
