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

    /// Mastodon API base URL for proxying requests fediway can't handle.
    /// e.g. `http://mastodon-web.mastodon.svc:3000`
    #[arg(long, env = "MASTODON_API_URL")]
    pub mastodon_api_url: Option<String>,

    /// Host that serves Mastodon media (avatars, headers, attachments).
    /// Defaults to `instance_domain` when unset. Set to your `S3_ALIAS_HOST`
    /// or CDN host if media is served from a separate origin.
    #[arg(long, env = "MEDIA_HOST")]
    pub media_host: Option<String>,

    /// Whether the Mastodon instance stores media in S3-compatible storage.
    /// Affects URL construction: S3 mode drops the `/system` path prefix and
    /// adds a `cache/` prefix for federated-account media.
    #[arg(long, env = "S3_ENABLED", default_value_t = false)]
    pub s3_enabled: bool,
}
