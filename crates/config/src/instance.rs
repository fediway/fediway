use clap::Args;

#[derive(Args, Debug, Clone)]
pub struct InstanceConfig {
    #[arg(long, env = "INSTANCE_DOMAIN")]
    pub instance_domain: String,

    #[arg(long, env = "INSTANCE_NAME")]
    pub instance_name: String,

    #[arg(long, env = "SERVER_HOST", default_value = "0.0.0.0")]
    pub server_host: String,

    #[arg(long, env = "SERVER_PORT", default_value_t = 3000)]
    pub server_port: u16,

    #[arg(long, env = "METRICS_PORT")]
    pub metrics_port: Option<u16>,
}
