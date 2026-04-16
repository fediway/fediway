use std::sync::Arc;
use std::time::Duration;

use sources::mastodon::MediaConfig;
use sqlx::PgPool;
use state::cache::Cache;

use crate::mastodon::resolve::Resolver;

pub type AppState = Arc<AppStateInner>;

pub struct AppStateInner {
    pub pool: PgPool,
    pub orbit_model_name: String,
    pub instance_domain: String,
    pub mastodon_api_url: Option<String>,
    pub cache: Cache,
    pub media: MediaConfig,
    pub http_client: reqwest::Client,
    pub resolver: Arc<Resolver>,
}

impl AppStateInner {
    #[must_use]
    pub fn new(
        pool: PgPool,
        cache: Cache,
        media: MediaConfig,
        orbit_model_name: String,
        instance_domain: String,
        mastodon_api_url: Option<String>,
    ) -> AppState {
        let mut default_headers = reqwest::header::HeaderMap::new();
        default_headers.insert(
            "x-forwarded-proto",
            reqwest::header::HeaderValue::from_static("https"),
        );
        let http_client = reqwest::Client::builder()
            .timeout(Duration::from_secs(10))
            .connect_timeout(Duration::from_secs(5))
            .redirect(reqwest::redirect::Policy::none())
            .default_headers(default_headers)
            .build()
            .expect("http client");

        let resolver = Resolver::new(
            pool.clone(),
            http_client.clone(),
            mastodon_api_url.clone(),
            instance_domain.clone(),
        );

        Arc::new(Self {
            pool,
            orbit_model_name,
            instance_domain,
            mastodon_api_url,
            cache,
            media,
            http_client,
            resolver,
        })
    }
}
