use axum::Json;
use axum::body::Bytes;
use axum::extract::{Path, State};
use axum::http::{HeaderMap, Method, StatusCode};
use axum::response::{IntoResponse, Response};
use serde_json::Value;

use crate::auth::Account;
use crate::mastodon::forward::forward;
use crate::mastodon::resolve::ResolveError;
use crate::mastodon::translate::translate_response;
use crate::routes::mastodon::error::EngagementError;
use crate::state::AppState;

#[derive(Clone, Copy)]
enum StatusAction {
    Favourite,
    Unfavourite,
    Reblog,
    Unreblog,
    Bookmark,
    Unbookmark,
}

impl StatusAction {
    fn segment(self) -> &'static str {
        match self {
            Self::Favourite => "favourite",
            Self::Unfavourite => "unfavourite",
            Self::Reblog => "reblog",
            Self::Unreblog => "unreblog",
            Self::Bookmark => "bookmark",
            Self::Unbookmark => "unbookmark",
        }
    }
}

pub async fn favourite(
    state: State<AppState>,
    account: Account,
    path: Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, EngagementError> {
    apply(state, account, path, headers, body, StatusAction::Favourite).await
}

pub async fn unfavourite(
    state: State<AppState>,
    account: Account,
    path: Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, EngagementError> {
    apply(
        state,
        account,
        path,
        headers,
        body,
        StatusAction::Unfavourite,
    )
    .await
}

pub async fn reblog(
    state: State<AppState>,
    account: Account,
    path: Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, EngagementError> {
    apply(state, account, path, headers, body, StatusAction::Reblog).await
}

pub async fn unreblog(
    state: State<AppState>,
    account: Account,
    path: Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, EngagementError> {
    apply(state, account, path, headers, body, StatusAction::Unreblog).await
}

pub async fn bookmark(
    state: State<AppState>,
    account: Account,
    path: Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, EngagementError> {
    apply(state, account, path, headers, body, StatusAction::Bookmark).await
}

pub async fn unbookmark(
    state: State<AppState>,
    account: Account,
    path: Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, EngagementError> {
    apply(
        state,
        account,
        path,
        headers,
        body,
        StatusAction::Unbookmark,
    )
    .await
}

async fn apply(
    State(state): State<AppState>,
    account: Account,
    Path(id): Path<String>,
    headers: HeaderMap,
    body: Bytes,
    action: StatusAction,
) -> Result<Response, EngagementError> {
    let result: Result<Response, EngagementError> = async {
        let (forward_id, hint_snowflake): (String, Option<i64>) = match id.parse::<i64>() {
            Ok(snowflake) => match state.resolver.resolve(snowflake, &account.token).await {
                Ok(mastodon_id) => (mastodon_id.to_string(), Some(snowflake)),
                // Pass the original id through and let Mastodon be authoritative.
                // Returning 404 here would double-proxy every native-timeline
                // engagement via the fallback middleware.
                Err(ResolveError::NotFound | ResolveError::Forbidden) => (id.clone(), None),
                Err(e) => return Err(e.into()),
            },
            Err(_) => (id.clone(), None),
        };

        let base_url = state
            .mastodon_api_url
            .as_deref()
            .ok_or(EngagementError::Unreachable)?;
        let path = format!("/api/v1/statuses/{forward_id}/{}", action.segment());

        let forwarded = forward(
            &state.http_client,
            base_url,
            Method::POST,
            &path,
            &headers,
            Some(body),
        )
        .await?;

        if !forwarded.status.is_success() {
            return Ok(forwarded.into_response());
        }

        let mut value: Value = serde_json::from_slice(&forwarded.body)?;
        translate_response(&state.pool, &mut value).await?;
        // Only pin the top-level id back to the caller's snowflake when the
        // response is still "about" the status we forwarded. Mastodon's
        // /reblog endpoint returns a freshly-created wrapper status with a
        // new id — rewriting that wrapper id to the original's snowflake
        // would attribute a brand-new post to the wrong handle.
        if let Some(snowflake) = hint_snowflake
            && let Some(id_field) = value.get_mut("id")
            && id_field.as_str() == Some(forward_id.as_str())
        {
            *id_field = Value::String(snowflake.to_string());
        }

        Ok((StatusCode::OK, Json(value)).into_response())
    }
    .await;

    let outcome = match &result {
        Ok(resp) if resp.status().is_success() => "ok",
        Ok(_) => "upstream_error",
        Err(e) => e.metric_outcome(),
    };
    metrics::counter!(
        "fediway_engagement_total",
        "action" => action.segment(),
        "outcome" => outcome,
    )
    .increment(1);

    result
}
