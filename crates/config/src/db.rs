use clap::Args;

#[derive(Args, Debug, Clone)]
pub struct DatabaseConfig {
    #[arg(long, env = "DB_HOST", default_value = "localhost")]
    pub db_host: String,

    #[arg(long, env = "DB_PORT", default_value_t = 5432)]
    pub db_port: u16,

    #[arg(long, env = "DB_NAME", default_value = "mastodon_development")]
    pub db_name: String,

    #[arg(long, env = "DB_USER", default_value = "mastodon")]
    pub db_user: String,

    #[arg(long, env = "DB_PASS")]
    pub db_pass: Option<String>,

    #[arg(long, env = "DB_POOL_SIZE", default_value_t = 10)]
    pub db_pool_size: u32,

    #[arg(long, env = "DB_POOL_MIN", default_value_t = 2)]
    pub db_pool_min: u32,

    /// Timeout in seconds to acquire a connection from the pool.
    #[arg(long, env = "DB_ACQUIRE_TIMEOUT", default_value_t = 3)]
    pub db_acquire_timeout_secs: u64,

    /// Idle timeout in seconds before a connection is closed.
    #[arg(long, env = "DB_IDLE_TIMEOUT", default_value_t = 600)]
    pub db_idle_timeout_secs: u64,

    /// Maximum lifetime in seconds before a connection is recycled.
    #[arg(long, env = "DB_MAX_LIFETIME", default_value_t = 1800)]
    pub db_max_lifetime_secs: u64,

    /// Maximum time in seconds for a single SQL statement. Enforced by Postgres.
    #[arg(long, env = "DB_STATEMENT_TIMEOUT", default_value_t = 30)]
    pub db_statement_timeout_secs: u64,

    /// Postgres `sslmode`. One of `disable`, `allow`, `prefer`, `require`,
    /// `verify-ca`, `verify-full`. Production deployments must set
    /// `verify-full`; `disable` is forbidden outside single-machine
    /// docker-compose.
    #[arg(long, env = "DB_SSL_MODE", default_value = "prefer")]
    pub db_ssl_mode: String,
}
