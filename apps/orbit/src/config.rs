
use serde::Deserialize;

fn default_rw_host() -> String { "localhost".into() }
fn default_rw_port() -> usize { 4566 }
fn default_rw_user() -> String { "root".into() }
fn default_rw_pass() -> String { "".into() }
fn default_rw_name() -> String { "dev".into() }
fn default_louvain_resolution() -> f64 { 1.0 }
fn default_louvain_max_iterations() -> usize { 100 }
fn default_random_state() -> u64 { 42 }

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

    #[serde(default = "default_random_state")]
    pub random_state: u64,
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
            self.rw_host, 
            self.rw_user, 
            self.rw_pass, 
            self.rw_name, 
            self.rw_port
        )
    }
}