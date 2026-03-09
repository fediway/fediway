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
