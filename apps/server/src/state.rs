use std::sync::Arc;

use sqlx::PgPool;

/// Shared application state passed to all handlers via axum's State extractor.
pub type AppState = Arc<AppStateInner>;

pub struct AppStateInner {
    pub pool: PgPool,
}

impl AppStateInner {
    #[must_use]
    pub fn new(pool: PgPool) -> AppState {
        Arc::new(Self { pool })
    }
}
