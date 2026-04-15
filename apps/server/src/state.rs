use std::sync::Arc;
use std::time::Duration;

use sources::mastodon::MediaConfig;
use sqlx::PgPool;
use state::feed_store::FeedStore;

use crate::mastodon::resolve::Resolver;

pub type AppState = Arc<AppStateInner>;

pub struct AppStateInner {
    pub pool: PgPool,
    pub orbit_model_name: String,
    pub instance_domain: String,
    pub mastodon_api_url: Option<String>,
    pub feed_store: FeedStore,
    pub media: MediaConfig,
    pub http_client: reqwest::Client,
    pub resolver: Arc<Resolver>,
}

impl AppStateInner {
    #[must_use]
    pub fn new(
        pool: PgPool,
        feed_store: FeedStore,
        media: MediaConfig,
        orbit_model_name: String,
        instance_domain: String,
        mastodon_api_url: Option<String>,
    ) -> AppState {
        let http_client = reqwest::Client::builder()
            .timeout(Duration::from_secs(10))
            .connect_timeout(Duration::from_secs(5))
            .redirect(reqwest::redirect::Policy::none())
            .build()
            .expect("http client");

        let resolver = Resolver::new(pool.clone(), http_client.clone(), mastodon_api_url.clone());

        Arc::new(Self {
            pool,
            orbit_model_name,
            instance_domain,
            mastodon_api_url,
            feed_store,
            media,
            http_client,
            resolver,
        })
    }
}
