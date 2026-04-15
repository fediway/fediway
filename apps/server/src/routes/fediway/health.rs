use std::error::Error;

use axum::Json;
use axum::extract::State;
use axum::http::StatusCode;

use crate::state::AppState;

pub async fn handle(State(state): State<AppState>) -> StatusCode {
    match sqlx::query("SELECT 1").execute(&state.pool).await {
        Ok(_) => StatusCode::OK,
        Err(_) => StatusCode::SERVICE_UNAVAILABLE,
    }
}

/// `GET /fediway/health/mastodon` — tests connectivity to Mastodon's API.
pub async fn mastodon(State(state): State<AppState>) -> (StatusCode, Json<serde_json::Value>) {
    let Some(base_url) = state.mastodon_api_url.as_deref() else {
        return (
            StatusCode::OK,
            Json(serde_json::json!({ "status": "not_configured" })),
        );
    };

    let url = format!("{base_url}/api/v1/instance");

    let result = state
        .http_client
        .get(&url)
        .header("Host", &state.instance_domain)
        .send()
        .await;

    match result {
        Ok(resp) => {
            let status = resp.status().as_u16();
            (
                StatusCode::OK,
                Json(serde_json::json!({
                    "status": "ok",
                    "mastodon_url": base_url,
                    "mastodon_status": status,
                })),
            )
        }
        Err(e) => {
            let detail = serde_json::json!({
                "status": "error",
                "mastodon_url": base_url,
                "error": e.to_string(),
                "is_connect": e.is_connect(),
                "is_timeout": e.is_timeout(),
                "source": e.source().map(ToString::to_string),
            });
            (StatusCode::BAD_GATEWAY, Json(detail))
        }
    }
}
