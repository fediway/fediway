use std::sync::LazyLock;
use std::time::Duration;

use axum::body::Body;
use axum::extract::Request;
use axum::http::{StatusCode, header};
use axum::middleware::Next;
use axum::response::{IntoResponse, Response};

use crate::state::AppState;

static HTTP_CLIENT: LazyLock<reqwest::Client> = LazyLock::new(|| {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .connect_timeout(Duration::from_secs(5))
        .build()
        .expect("http client")
});

/// Middleware that proxies to Mastodon when the inner handler returns 404.
/// Forwards the original path and Authorization header.
/// No-op if `MASTODON_API_URL` is not configured.
pub async fn fallback(state: axum::extract::State<AppState>, req: Request, next: Next) -> Response {
    let base_url = match state.mastodon_api_url.as_deref() {
        Some(url) => url.to_string(),
        None => return next.run(req).await,
    };

    let path = req.uri().path_and_query().map(ToString::to_string);
    let auth = req.headers().get(header::AUTHORIZATION).cloned();

    let response = next.run(req).await;

    if response.status() != StatusCode::NOT_FOUND {
        return response;
    }

    let Some(path) = path else {
        return response;
    };

    let mut proxy_req = HTTP_CLIENT.get(format!("{base_url}{path}"));
    if let Some(auth) = auth {
        proxy_req = proxy_req.header(header::AUTHORIZATION, auth);
    }

    let proxy_resp = match proxy_req.send().await {
        Ok(r) => r,
        Err(e) => {
            tracing::warn!(error = %e, path, "mastodon fallback request failed");
            return StatusCode::BAD_GATEWAY.into_response();
        }
    };

    let status =
        StatusCode::from_u16(proxy_resp.status().as_u16()).unwrap_or(StatusCode::BAD_GATEWAY);
    let content_type = proxy_resp.headers().get(header::CONTENT_TYPE).cloned();
    let body = match proxy_resp.bytes().await {
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
