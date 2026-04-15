use axum::Json;
use axum::body::Bytes;
use axum::extract::State;
use axum::http::{HeaderMap, Method, StatusCode, header};
use axum::response::{IntoResponse, Response};
use serde_json::Value;

use crate::auth::Account;
use crate::mastodon::forward::forward;
use crate::mastodon::translate::translate_request_id;
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

    let is_json = headers
        .get(header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .is_some_and(|s| s.starts_with("application/json"));

    let forward_body = if is_json {
        let mut value: Value = serde_json::from_slice(&body)?;
        if let Some(Value::Array(ids)) = value.get_mut("status_ids") {
            for id_value in ids.iter_mut() {
                if let Value::String(id) = id_value {
                    translate_request_id(&state.resolver, &account.token, id).await?;
                }
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
        "/api/v1/reports",
        &headers,
        Some(forward_body),
    )
    .await?;

    if !forwarded.status.is_success() {
        return Ok(forwarded.into_response());
    }

    let mut value: Value = serde_json::from_slice(&forwarded.body)?;
    if let Some(ids) = value.get_mut("status_ids").and_then(Value::as_array_mut) {
        let mastodon_ids: Vec<i64> = ids
            .iter()
            .filter_map(|v| v.as_str().and_then(|s| s.parse::<i64>().ok()))
            .collect();
        if !mastodon_ids.is_empty() {
            let map = state::statuses::reverse_map(&state.pool, &mastodon_ids).await?;
            for id_value in ids {
                let Some(n) = id_value.as_str().and_then(|s| s.parse::<i64>().ok()) else {
                    continue;
                };
                if let Some(&snowflake) = map.get(&n) {
                    *id_value = Value::String(snowflake.to_string());
                }
            }
        }
    }

    Ok((StatusCode::OK, Json(value)).into_response())
}
