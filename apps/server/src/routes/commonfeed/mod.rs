mod callback;
mod verify;

use axum::Router;
use axum::routing::{get, post};

use crate::state::AppState;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/.well-known/commonfeed/{token}", get(verify::handle))
        .route("/commonfeed/callback", post(callback::handle))
}
