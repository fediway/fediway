use clap::Args;

#[derive(Args, Debug, Clone)]
pub struct TeiConfig {
    /// TEI HTTP endpoint
    #[arg(long, env = "TEI_URL", default_value = "http://localhost:8080")]
    pub tei_url: String,

    /// Request timeout in seconds
    #[arg(long, env = "TEI_TIMEOUT_SECS", default_value_t = 30)]
    pub tei_timeout_secs: u64,

    /// Maximum texts per embedding batch
    #[arg(long, env = "TEI_BATCH_SIZE", default_value_t = 64)]
    pub tei_batch_size: usize,
}
