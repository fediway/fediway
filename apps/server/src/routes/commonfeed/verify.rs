use axum::extract::{Path, State};
use axum::http::StatusCode;
use sqlx::PgPool;

pub async fn handle(State(db): State<PgPool>, Path(token): Path<String>) -> StatusCode {
    let verify_path = format!("/.well-known/commonfeed/{token}");

    let exists = sqlx::query_scalar::<_, bool>(
        "SELECT EXISTS(
            SELECT 1 FROM commonfeed_providers
            WHERE verify_path = $1 AND status = 'pending'
        )",
    )
    .bind(&verify_path)
    .fetch_one(&db)
    .await
    .unwrap_or(false);

    if exists {
        StatusCode::OK
    } else {
        StatusCode::NOT_FOUND
    }
}
