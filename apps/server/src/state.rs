use std::sync::Arc;

use sqlx::PgPool;
use state::feed_store::FeedStore;

pub type AppState = Arc<AppStateInner>;

pub struct AppStateInner {
    pub pool: PgPool,
    pub orbit_model_name: String,
    pub instance_domain: String,
    pub mastodon_api_url: Option<String>,
    pub feed_store: FeedStore,
}

impl AppStateInner {
    #[must_use]
    pub fn new(
        pool: PgPool,
        feed_store: FeedStore,
        orbit_model_name: String,
        instance_domain: String,
        mastodon_api_url: Option<String>,
    ) -> AppState {
        Arc::new(Self {
            pool,
            orbit_model_name,
            instance_domain,
            mastodon_api_url,
            feed_store,
        })
    }
}
