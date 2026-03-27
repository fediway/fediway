use clap::Args;

#[derive(Args, Debug, Clone)]
pub struct OrbitConfig {
    /// EMA learning rate (must match provider-side Orbit02: 0.05)
    #[arg(long, env = "ORBIT_ALPHA", default_value_t = 0.05)]
    pub orbit_alpha: f64,

    /// Embedding dimensionality after MRL truncation (must match provider)
    #[arg(long, env = "ORBIT_DIMS", default_value_t = 64)]
    pub orbit_dims: usize,

    /// Seconds between engagement poll cycles
    #[arg(long, env = "ORBIT_POLL_INTERVAL_SECS", default_value_t = 10)]
    pub orbit_poll_interval_secs: u64,

    /// Maximum engagements to process per poll cycle
    #[arg(long, env = "ORBIT_BATCH_SIZE", default_value_t = 500)]
    pub orbit_batch_size: i64,

    /// Embedding model name sent to provider (must match provider capability)
    #[arg(long, env = "ORBIT_MODEL_NAME", default_value = "bge_small_64d")]
    pub orbit_model_name: String,

    /// On first startup, only process engagements from the last N hours.
    /// Avoids flooding TEI with years of historical data.
    /// Set to 0 to process all history (not recommended).
    #[arg(long, env = "ORBIT_REPLAY_HOURS", default_value_t = 168)]
    pub orbit_replay_hours: u64,
}
