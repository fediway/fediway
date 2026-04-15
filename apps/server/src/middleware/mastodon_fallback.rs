use std::error::Error;

use axum::body::Body;
use axum::extract::Request;
use axum::http::{HeaderMap, Method, StatusCode, header};
use axum::middleware::Next;
use axum::response::{IntoResponse, Response};

use crate::state::AppState;

const MAX_PROXY_BODY_BYTES: usize = 1_048_576;

/// Marks a response as final — the fallback middleware will not proxy it
/// to Mastodon even if it carries a 404/405 status. Handlers set this when
/// they own the route and any error is a real terminal failure (e.g. the
/// resolver refused to produce a mastodon id), distinguishing those cases
/// from unhandled-route 404s emitted by [`statuses::proxy_fallback`].
#[derive(Clone, Copy)]
pub struct NoFallback;

/// Proxies unhandled Mastodon API calls to the upstream instance.
///
/// The inner router runs first for every request; a 404 or 405 response
/// triggers a proxy to Mastodon with the original method, headers, and body.
/// No-op if `MASTODON_API_URL` is not configured. Handler-owned routes that
/// want to emit a final 404 must attach [`NoFallback`] to their response.
pub async fn fallback(state: axum::extract::State<AppState>, req: Request, next: Next) -> Response {
    let Some(base_url) = state.mastodon_api_url.clone() else {
        return next.run(req).await;
    };

    let method = req.method().clone();
    let headers = req.headers().clone();
    let Some(path) = req.uri().path_and_query().map(ToString::to_string) else {
        return next.run(req).await;
    };

    let (buffered, forward_req) = if method == Method::GET {
        (None, req)
    } else {
        let (parts, body) = req.into_parts();
        let bytes = match axum::body::to_bytes(body, MAX_PROXY_BODY_BYTES).await {
            Ok(b) => b,
            Err(e) => {
                tracing::warn!(error = %e, "request body too large or unreadable");
                return StatusCode::PAYLOAD_TOO_LARGE.into_response();
            }
        };
        let forward = Request::from_parts(parts, Body::from(bytes.clone()));
        (Some(bytes), forward)
    };

    let response = next.run(forward_req).await;

    if response.extensions().get::<NoFallback>().is_some() {
        return response;
    }

    let status = response.status();
    if status != StatusCode::NOT_FOUND && status != StatusCode::METHOD_NOT_ALLOWED {
        return response;
    }

    proxy(
        &state.http_client,
        &base_url,
        &path,
        &method,
        &headers,
        buffered.as_deref(),
    )
    .await
}

async fn proxy(
    http: &reqwest::Client,
    base_url: &str,
    path: &str,
    method: &Method,
    headers: &HeaderMap,
    body: Option<&[u8]>,
) -> Response {
    let url = format!("{base_url}{path}");

    let mut req = http.request(method.clone(), &url);

    for (name, value) in headers {
        req = req.header(name, value);
    }

    if let Some(body) = body {
        req = req.body(body.to_vec());
    }

    let resp = match req.send().await {
        Ok(r) => r,
        Err(e) => {
            tracing::warn!(
                url,
                method = %method,
                error = %e,
                error_source = e.source().map(ToString::to_string),
                is_connect = e.is_connect(),
                is_timeout = e.is_timeout(),
                "mastodon fallback failed"
            );
            return StatusCode::BAD_GATEWAY.into_response();
        }
    };

    let status = StatusCode::from_u16(resp.status().as_u16()).unwrap_or(StatusCode::BAD_GATEWAY);
    let content_type = resp.headers().get(header::CONTENT_TYPE).cloned();
    let body = match resp.bytes().await {
        Ok(b) => b,
        Err(e) => {
            tracing::warn!(error = %e, "mastodon fallback response read failed");
            return StatusCode::BAD_GATEWAY.into_response();
        }
    };

    let mut response = (status, Body::from(body)).into_response();
    if let Some(ct) = content_type {
        response.headers_mut().insert(header::CONTENT_TYPE, ct);
    }
    response
}
