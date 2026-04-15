use axum::Json;
use axum::body::Bytes;
use axum::extract::State;
use axum::http::{HeaderMap, Method, StatusCode, header};
use axum::response::{IntoResponse, Response};
use serde_json::Value;

use crate::auth::Account;
use crate::mastodon::forward::forward;
use crate::mastodon::translate::{translate_request_id, translate_response};
use crate::routes::mastodon::error::EngagementError;
use crate::state::AppState;

pub async fn handle(
    State(state): State<AppState>,
    account: Account,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, EngagementError> {
    let base_url = state
        .mastodon_api_url
        .as_deref()
        .ok_or(EngagementError::Unreachable)?;

    // Form-encoded and multipart bodies are forwarded untouched: the old
    // middleware-proxy path preserved them, and parsing either shape here
    // would need a dedicated codec. JSON clients are the common case and
    // get full id translation; form-encoded clients fall back to legacy
    // behaviour until there's demand to plumb through a parser.
    let is_json = headers
        .get(header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .is_some_and(|s| s.starts_with("application/json"));

    let forward_body = if is_json {
        let mut value: Value = serde_json::from_slice(&body)?;
        for key in ["in_reply_to_id", "quote_id"] {
            if let Some(Value::String(id)) = value.get_mut(key) {
                translate_request_id(&state.resolver, &account.token, id).await?;
            }
        }
        Bytes::from(
            serde_json::to_vec(&value).expect("re-serializing a deserialized Value cannot fail"),
        )
    } else {
        body
    };

    let forwarded = forward(
        &state.http_client,
        base_url,
        Method::POST,
        "/api/v1/statuses",
        &headers,
        Some(forward_body),
    )
    .await?;

    if !forwarded.status.is_success() {
        return Ok(forwarded.into_response());
    }

    let mut value: Value = serde_json::from_slice(&forwarded.body)?;
    translate_response(&state.pool, &mut value).await?;
    Ok((StatusCode::OK, Json(value)).into_response())
}
