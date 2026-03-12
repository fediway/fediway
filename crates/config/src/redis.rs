use clap::Args;

#[derive(Args, Debug, Clone)]
pub struct RedisConfig {
    #[arg(long, env = "REDIS_HOST", default_value = "localhost")]
    pub redis_host: String,

    #[arg(long, env = "REDIS_PORT", default_value_t = 6379)]
    pub redis_port: u16,
}
