use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct RedisConfig {
    #[serde(default = "default_host")]
    pub redis_host: String,
    #[serde(default = "default_port")]
    pub redis_port: u16,
}

fn default_host() -> String {
    "localhost".to_string()
}
fn default_port() -> u16 {
    6379
}
