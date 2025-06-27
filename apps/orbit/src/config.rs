use serde::Deserialize;

fn default_rw_host() -> String {
    "localhost".into()
}
fn default_rw_port() -> usize {
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
fn default_max_producer_communities() -> usize {
    20
}
fn default_max_consumer_communities() -> usize {
    50
}
fn default_max_tag_communities() -> usize {
    16
}
fn default_max_status_communities() -> usize {
    100
}
fn default_lambda() -> f64 {
    0.05
}
fn default_workers() -> usize {
    4
}

#[derive(Clone, Debug, Deserialize)]
pub struct Config {
    #[serde(default = "default_rw_host")]
    pub rw_host: String,

    #[serde(default = "default_rw_port")]
    pub rw_port: usize,

    #[serde(default = "default_rw_user")]
    pub rw_user: String,

    #[serde(default = "default_rw_pass")]
    pub rw_pass: String,

    #[serde(default = "default_rw_name")]
    pub rw_name: String,

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
        rename = "orbit_max_producer_communities",
        default = "default_max_producer_communities"
    )]
    pub max_producer_communities: usize,

    #[serde(
        rename = "orbit_max_consumer_communities",
        default = "default_max_consumer_communities"
    )]
    pub max_consumer_communities: usize,

    #[serde(
        rename = "orbit_max_tag_communities",
        default = "default_max_tag_communities"
    )]
    pub max_tag_communities: usize,

    #[serde(
        rename = "orbit_max_status_communities",
        default = "default_max_status_communities"
    )]
    pub max_status_communities: usize,

    #[serde(rename = "orbit_lambda", default = "default_lambda")]
    pub lambda: f64,

    #[serde(rename = "orbit_workers", default = "default_workers")]
    pub workers: usize,
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
}
