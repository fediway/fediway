use axum::extract::{Path, State};
use axum::http::StatusCode;

use crate::state::AppState;

pub async fn handle(State(state): State<AppState>, Path(token): Path<String>) -> StatusCode {
    let verify_path = format!("/.well-known/commonfeed/{token}");

    let exists = sqlx::query_scalar::<_, bool>(
        "SELECT EXISTS(
            SELECT 1 FROM commonfeed_providers
            WHERE verify_path = $1 AND status = 'pending'
        )",
    )
    .bind(&verify_path)
    .fetch_one(&state.pool)
    .await
    .unwrap_or(false);

    if exists {
        StatusCode::OK
    } else {
        StatusCode::NOT_FOUND
    }
}
