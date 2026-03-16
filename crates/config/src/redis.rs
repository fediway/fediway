use clap::Args;

#[derive(Args, Debug, Clone)]
pub struct RedisConfig {
    #[arg(long, env = "REDIS_HOST", default_value = "localhost")]
    pub redis_host: String,

    #[arg(long, env = "REDIS_PORT", default_value_t = 6379)]
    pub redis_port: u16,

    #[arg(long, env = "REDIS_PASS", default_value = "")]
    pub redis_pass: String,
}

impl RedisConfig {
    #[must_use]
    pub fn url(&self) -> String {
        if self.redis_pass.is_empty() {
            format!("redis://{}:{}", self.redis_host, self.redis_port)
        } else {
            format!(
                "redis://:{}@{}:{}",
                self.redis_pass, self.redis_host, self.redis_port
            )
        }
    }
}
