use std::sync::Arc;

use sqlx::PgPool;

/// Shared application state passed to all handlers via axum's State extractor.
pub type AppState = Arc<AppStateInner>;

pub struct AppStateInner {
    pub pool: PgPool,
    pub orbit_model_name: String,
    pub instance_domain: String,
}

impl AppStateInner {
    #[must_use]
    pub fn new(pool: PgPool, orbit_model_name: String, instance_domain: String) -> AppState {
        Arc::new(Self {
            pool,
            orbit_model_name,
            instance_domain,
        })
    }
}
