use std::time::Duration;

use axum::Json;
use axum::extract::{Path, State};
use axum::http::{HeaderMap, Method, StatusCode};
use axum::response::{IntoResponse, Response};
use common::types::Post;
use mastodon::{Context, Status};
use serde_json::Value;

use crate::auth::Account;
use crate::mastodon::forward::forward;
use crate::mastodon::resolve::ResolveError;
use crate::mastodon::translate::translate_response;
use crate::state::AppState;

const CACHE_TTL: Duration = Duration::from_secs(3600);

/// Catch-all for unhandled statuses routes. Returns 404 which the
/// `mastodon_fallback` middleware intercepts and proxies to Mastodon.
pub async fn proxy_fallback() -> StatusCode {
    StatusCode::NOT_FOUND
}

/// `GET /api/v1/statuses/:id` — single status detail.
pub async fn detail(
    State(state): State<AppState>,
    account: Option<Account>,
    Path(id): Path<String>,
    headers: HeaderMap,
) -> Result<Response, StatusCode> {
    let snowflake: i64 = id.parse().map_err(|_| StatusCode::NOT_FOUND)?;

    let mut row = state::statuses::find_by_id(&state.pool, snowflake)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .ok_or(StatusCode::NOT_FOUND)?;

    // An authenticated viewer hitting a commonfeed recommendation for the
    // first time triggers a one-shot resolve so the post-resolve proxy path
    // below can surface fresh counters and per-user flags. Anonymous callers
    // skip this: they have no per-user state to gain and shouldn't pay the
    // federation round-trip.
    if row.mastodon_local_id.is_none()
        && let Some(account) = account.as_ref()
    {
        match state.resolver.resolve(snowflake, &account.token).await {
            Ok(mastodon_id) => row.mastodon_local_id = Some(mastodon_id),
            Err(ResolveError::NotFound | ResolveError::Forbidden | ResolveError::Unresolvable) => {}
            Err(e) => {
                tracing::warn!(error = ?e, snowflake, "detail: first-view resolve failed");
            }
        }
    }

    // Once we know the Mastodon local id, let Mastodon serve: it has fresher
    // engagement counters and per-user flags (favourited / bookmarked / muted)
    // that the cached `post_data` can't provide.
    if let (Some(mastodon_local_id), Some(base_url)) =
        (row.mastodon_local_id, state.mastodon_api_url.as_deref())
    {
        let path = format!("/api/v1/statuses/{mastodon_local_id}");
        match forward(
            &state.http_client,
            base_url,
            Method::GET,
            &path,
            &headers,
            None,
        )
        .await
        {
            Ok(forwarded) if forwarded.status.is_success() => {
                match serde_json::from_slice::<Value>(&forwarded.body) {
                    Ok(mut value) => {
                        if translate_response(&state.pool, &mut value).await.is_ok() {
                            if let Some(id_field) = value.get_mut("id") {
                                *id_field = Value::String(snowflake.to_string());
                            }
                            return Ok((StatusCode::OK, Json(value)).into_response());
                        }
                    }
                    Err(e) => {
                        tracing::warn!(
                            error = %e,
                            snowflake,
                            "detail: failed to parse mastodon response"
                        );
                    }
                }
            }
            Ok(forwarded)
                if forwarded.status == StatusCode::NOT_FOUND
                    || forwarded.status == StatusCode::GONE =>
            {
                let _ = state::statuses::clear_mastodon_local_id(&state.pool, row.id).await;
            }
            Ok(forwarded) => return Ok(forwarded.into_response()),
            Err(_) => {}
        }
    }

    let post_data = if row.is_stale(CACHE_TTL) {
        match refresh_from_provider(&state, &row).await {
            Ok(fresh) => fresh,
            Err(_) => row.post_data,
        }
    } else {
        row.post_data
    };

    let post: Post = serde_json::from_value(post_data).map_err(|e| {
        tracing::warn!(id = snowflake, error = %e, "failed to deserialize cached post");
        StatusCode::INTERNAL_SERVER_ERROR
    })?;

    let status = Status::from_post(post, snowflake.to_string());
    Ok(Json(status).into_response())
}

/// `GET /api/v1/statuses/:id/context` — ancestors and descendants.
pub async fn context(
    State(state): State<AppState>,
    Path(id): Path<String>,
    headers: HeaderMap,
) -> Result<Response, StatusCode> {
    let snowflake: i64 = id.parse().map_err(|_| StatusCode::NOT_FOUND)?;

    let row = state::statuses::find_by_id(&state.pool, snowflake)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .ok_or(StatusCode::NOT_FOUND)?;

    // Once resolved, Mastodon's /context is the canonical reply tree; it
    // fills gaps that our cached `reply_to` walk + provider-side descendants
    // fetch can't cover.
    if let (Some(mastodon_local_id), Some(base_url)) =
        (row.mastodon_local_id, state.mastodon_api_url.as_deref())
    {
        let path = format!("/api/v1/statuses/{mastodon_local_id}/context");
        match forward(
            &state.http_client,
            base_url,
            Method::GET,
            &path,
            &headers,
            None,
        )
        .await
        {
            Ok(forwarded) if forwarded.status.is_success() => {
                match serde_json::from_slice::<Value>(&forwarded.body) {
                    Ok(mut value) => {
                        let mut translate_ok = true;
                        for key in ["ancestors", "descendants"] {
                            let Some(arr) = value.get_mut(key).and_then(Value::as_array_mut) else {
                                continue;
                            };
                            for item in arr {
                                if let Err(e) = translate_response(&state.pool, item).await {
                                    tracing::warn!(
                                        error = %e,
                                        snowflake,
                                        "context: reverse-map failed"
                                    );
                                    translate_ok = false;
                                    break;
                                }
                            }
                            if !translate_ok {
                                break;
                            }
                        }
                        if translate_ok {
                            return Ok((StatusCode::OK, Json(value)).into_response());
                        }
                    }
                    Err(e) => {
                        tracing::warn!(
                            error = %e,
                            snowflake,
                            "context: failed to parse mastodon response"
                        );
                    }
                }
            }
            Ok(forwarded)
                if forwarded.status == StatusCode::NOT_FOUND
                    || forwarded.status == StatusCode::GONE =>
            {
                let _ = state::statuses::clear_mastodon_local_id(&state.pool, row.id).await;
            }
            Ok(forwarded) => return Ok(forwarded.into_response()),
            Err(_) => {}
        }
    }

    let ancestors = build_ancestors(&state, &row.post_data).await;
    let descendants = fetch_descendants(&state, &row).await;

    Ok(Json(Context {
        ancestors,
        descendants,
    })
    .into_response())
}

async fn build_ancestors(state: &AppState, post_data: &serde_json::Value) -> Vec<Status> {
    let mut posts = Vec::new();
    let mut current = post_data.clone();
    let max_depth = 20;

    for _ in 0..max_depth {
        let reply_to = current
            .get("reply_to")
            .or_else(|| current.get("replyTo"))
            .cloned();
        let Some(parent_data) = reply_to else { break };
        if parent_data.is_null() {
            break;
        }

        let parent_post: Post = match serde_json::from_value(parent_data.clone()) {
            Ok(p) => p,
            Err(_) => break,
        };

        posts.push(parent_post);
        current = parent_data;
    }

    let mut ancestors =
        crate::mastodon::statuses::from_posts(&state.pool, &state.instance_domain, posts).await;
    ancestors.reverse();
    ancestors
}

const DESCENDANTS_PAGE_LIMIT: u32 = 60;
const DESCENDANTS_MAX_PAGES: u32 = 5;

async fn fetch_descendants(state: &AppState, row: &state::statuses::CachedStatus) -> Vec<Status> {
    let provider = match state::providers::find_by_domain(&state.pool, &row.provider_domain).await {
        Ok(Some(p)) => p,
        Ok(None) => return Vec::new(),
        Err(e) => {
            tracing::warn!(error = %e, domain = %row.provider_domain, "provider lookup failed");
            return Vec::new();
        }
    };

    let base_url = format!("{}/posts/{}/replies", provider.base_url, row.remote_id);
    let mut all_posts: Vec<Post> = Vec::new();
    let mut cursor: Option<String> = None;

    for _ in 0..DESCENDANTS_MAX_PAGES {
        let mut req = state
            .http_client
            .get(&base_url)
            .bearer_auth(&provider.api_key)
            .query(&[("limit", &DESCENDANTS_PAGE_LIMIT.to_string())]);

        if let Some(c) = &cursor {
            req = req.query(&[("cursor", c)]);
        }

        let resp = match req.send().await {
            Ok(r) if r.status().is_success() => r,
            Ok(r) => {
                tracing::warn!(status = %r.status(), url = %base_url, "provider replies request failed");
                break;
            }
            Err(e) => {
                tracing::warn!(error = %e, url = %base_url, "provider replies request error");
                break;
            }
        };

        let body: sources::commonfeed::types::NavigationResponse = match resp.json().await {
            Ok(b) => b,
            Err(e) => {
                tracing::warn!(error = %e, "failed to parse provider replies response");
                break;
            }
        };

        let has_more = body.pagination.has_more;
        let next_cursor = body.pagination.cursor;

        all_posts.extend(
            body.results
                .into_iter()
                .map(|r| sources::commonfeed::posts::post_from_result(r, &provider.domain)),
        );

        if !has_more {
            break;
        }

        cursor = next_cursor;
    }

    crate::mastodon::statuses::from_posts(&state.pool, &state.instance_domain, all_posts).await
}

async fn refresh_from_provider(
    state: &AppState,
    row: &state::statuses::CachedStatus,
) -> Result<serde_json::Value, StatusCode> {
    let provider = state::providers::find_by_domain(&state.pool, &row.provider_domain)
        .await
        .map_err(|e| {
            tracing::warn!(error = %e, domain = %row.provider_domain, "provider lookup failed");
            StatusCode::INTERNAL_SERVER_ERROR
        })?
        .ok_or(StatusCode::NOT_FOUND)?;

    let url = format!("{}/posts/{}", provider.base_url, row.remote_id);

    let resp = state
        .http_client
        .get(&url)
        .bearer_auth(&provider.api_key)
        .send()
        .await
        .map_err(|e| {
            tracing::warn!(error = %e, "provider refresh request failed");
            StatusCode::BAD_GATEWAY
        })?;

    match resp.status().as_u16() {
        200 => {}
        404 | 410 => {
            let _ = state::statuses::delete(&state.pool, row.id).await;
            return Err(StatusCode::NOT_FOUND);
        }
        status => {
            tracing::warn!(status, "provider refresh returned error");
            return Err(StatusCode::BAD_GATEWAY);
        }
    }

    let body: sources::commonfeed::types::PostLookupResponse = resp.json().await.map_err(|e| {
        tracing::warn!(error = %e, "failed to parse provider lookup response");
        StatusCode::BAD_GATEWAY
    })?;

    let post = sources::commonfeed::posts::post_from_result(body.post, &row.provider_domain);
    let post_data = serde_json::to_value(&post).unwrap_or_default();

    let _ = state::statuses::update_cache(&state.pool, row.id, &post_data).await;

    Ok(post_data)
}
