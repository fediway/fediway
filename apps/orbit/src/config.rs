use crate::communities::Communities;
use qdrant_client::config::QdrantConfig;
use redis::{ConnectionAddr, ConnectionInfo, ProtocolVersion, RedisConnectionInfo};
use serde::Deserialize;

fn default_rw_host() -> String {
    "localhost".into()
}
fn default_rw_port() -> u16 {
    4566
}
fn default_rw_user() -> String {
    "root".into()
}
fn default_rw_pass() -> String {
    "".into()
}
fn default_rw_name() -> String {
    "dev".into()
}

fn default_db_host() -> String {
    "localhost".into()
}
fn default_db_port() -> u16 {
    5432
}
fn default_db_user() -> String {
    "mastodon".into()
}
fn default_db_pass() -> String {
    "".into()
}
fn default_db_name() -> String {
    "mastodon_development".into()
}

fn default_redis_host() -> String {
    "localhost".into()
}
fn default_redis_port() -> u16 {
    6379
}
fn default_redis_pass() -> Option<String> {
    None
}
fn default_redis_name() -> i64 {
    0
}
fn default_louvain_resolution() -> f64 {
    1.0
}
fn default_louvain_max_iterations() -> usize {
    100
}
fn default_random_state() -> u64 {
    42
}
fn default_tag_sim_threshold() -> f64 {
    0.25
}
fn default_workers() -> usize {
    4
}
fn default_kafka_bootstrap_servers() -> String {
    "localhost:29092".into()
}
fn default_kafka_group_id() -> String {
    "orbit".into()
}
fn default_qdrant_host() -> String {
    "localhost".into()
}
fn default_qdrant_port() -> u16 {
    6334
}
fn default_qdrant_collection_prefix() -> String {
    "orbit".into()
}
fn default_qdrant_max_batch_size() -> usize {
    500
}
fn default_producer_engagement_threshold() -> usize {
    50
}
fn default_status_engagement_threshold() -> usize {
    1
}
fn default_tag_engagement_threshold() -> usize {
    10
}
fn default_qdrant_upsert_delay() -> u64 {
    60 // 60 seconds
}
fn default_max_status_age() -> u64 {
    60 * 60 * 24 * 7 // 7 days
}
fn default_min_tag_authors() -> usize {
    5
}
fn default_min_tag_engagers() -> usize {
    15
}

#[derive(Clone, Debug, Deserialize)]
pub struct Config {
    #[serde(default = "default_rw_host")]
    pub rw_host: String,

    #[serde(default = "default_rw_port")]
    pub rw_port: u16,

    #[serde(default = "default_rw_user")]
    pub rw_user: String,

    #[serde(default = "default_rw_pass")]
    pub rw_pass: String,

    #[serde(default = "default_rw_name")]
    pub rw_name: String,

    #[serde(default = "default_db_host")]
    pub db_host: String,

    #[serde(default = "default_db_port")]
    pub db_port: u16,

    #[serde(default = "default_db_user")]
    pub db_user: String,

    #[serde(default = "default_db_pass")]
    pub db_pass: String,

    #[serde(default = "default_db_name")]
    pub db_name: String,

    #[serde(default = "default_redis_host")]
    pub redis_host: String,

    #[serde(default = "default_redis_port")]
    pub redis_port: u16,

    #[serde(default = "default_redis_pass")]
    pub redis_pass: Option<String>,

    #[serde(default = "default_redis_name")]
    pub redis_name: i64,

    #[serde(default = "default_qdrant_host")]
    pub qdrant_host: String,

    #[serde(default = "default_qdrant_port")]
    pub qdrant_port: u16,

    #[serde(default = "default_kafka_bootstrap_servers")]
    pub kafka_bootstrap_servers: String,

    #[serde(default = "default_kafka_group_id")]
    pub kafka_group_id: String,

    #[serde(
        rename = "orbit_qdrant_collection_prefix",
        default = "default_qdrant_collection_prefix"
    )]
    pub qdrant_collection_prefix: String,

    #[serde(
        rename = "orbit_qdrant_max_batch_size",
        default = "default_qdrant_max_batch_size"
    )]
    pub qdrant_max_batch_size: usize,

    #[serde(
        rename = "orbit_qdrant_upsert_delay",
        default = "default_qdrant_upsert_delay"
    )]
    pub qdrant_upsert_delay: u64,

    #[serde(
        rename = "orbit_louvain_resolution",
        default = "default_louvain_resolution"
    )]
    pub louvain_resolution: f64,

    #[serde(
        rename = "orbit_louvain_max_iterations",
        default = "default_louvain_max_iterations"
    )]
    pub louvain_max_iterations: usize,

    #[serde(
        rename = "orbit_tag_sim_threshold",
        default = "default_tag_sim_threshold"
    )]
    pub tag_sim_threshold: f64,

    #[serde(default = "default_random_state")]
    pub random_state: u64,

    #[serde(
        rename = "orbit_status_engagement_threshold",
        default = "default_status_engagement_threshold"
    )]
    pub status_engagement_threshold: usize,

    #[serde(
        rename = "orbit_producer_engagement_threshold",
        default = "default_producer_engagement_threshold"
    )]
    pub producer_engagement_threshold: usize,

    #[serde(
        rename = "orbit_tag_engagement_threshold",
        default = "default_tag_engagement_threshold"
    )]
    pub tag_engagement_threshold: usize,

    #[serde(rename = "orbit_max_status_age", default = "default_max_status_age")]
    pub max_status_age: u64,

    #[serde(rename = "orbit_workers", default = "default_workers")]
    pub workers: usize,

    #[serde(rename = "orbit_min_tag_authors", default = "default_min_tag_authors")]
    pub min_tag_authors: usize,

    #[serde(
        rename = "orbit_min_tag_engagers",
        default = "default_min_tag_engagers"
    )]
    pub min_tag_engagers: usize,

    #[serde(rename = "orbit_tags_blacklist", default = "Vec::default")]
    pub tags_blacklist: Vec<String>,
}

impl Config {
    pub fn from_env() -> Self {
        // load .env file if exists
        dotenvy::from_filename("../../.env").ok();

        envy::from_env::<Config>().unwrap()
    }

    pub fn rw_conn(&self) -> String {
        format!(
            "host={} user={} password={} dbname={} port={}",
            self.rw_host, self.rw_user, self.rw_pass, self.rw_name, self.rw_port
        )
    }

    pub fn db_conn(&self) -> String {
        format!(
            "host={} user={} password={} dbname={} port={}",
            self.db_host, self.db_user, self.db_pass, self.db_name, self.db_port
        )
    }

    pub fn redis_conn(&self) -> ConnectionInfo {
        ConnectionInfo {
            addr: ConnectionAddr::Tcp(self.redis_host.clone(), self.redis_port),
            redis: RedisConnectionInfo {
                db: self.redis_name,
                username: None,
                password: self.redis_pass.clone(),
                protocol: ProtocolVersion::default(),
            },
        }
    }

    pub fn qdrant_url(&self) -> String {
        format!("http://{}:{}", self.qdrant_host, self.qdrant_port)
    }

    pub fn qdrant_config(&self) -> QdrantConfig {
        QdrantConfig::from_url(&self.qdrant_url())
    }

    pub fn qdrant_collection_name(&self, communities: &Communities) -> String {
        format!(
            "{}_{}",
            self.qdrant_collection_prefix,
            communities.version()
        )
    }
}
