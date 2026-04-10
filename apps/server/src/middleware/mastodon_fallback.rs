use std::error::Error;
use std::sync::LazyLock;
use std::time::Duration;

use axum::body::Body;
use axum::extract::Request;
use axum::http::{HeaderMap, Method, StatusCode, header};
use axum::middleware::Next;
use axum::response::{IntoResponse, Response};

use crate::state::AppState;

static HTTP_CLIENT: LazyLock<reqwest::Client> = LazyLock::new(|| {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .connect_timeout(Duration::from_secs(5))
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .expect("http client")
});

/// Middleware that proxies requests to Mastodon.
///
/// - **GET**: runs the inner handler first; proxies to Mastodon on 404.
/// - **Non-GET** (DELETE, PUT, POST): proxies to Mastodon immediately with body.
/// - No-op if `MASTODON_API_URL` is not configured.
pub async fn fallback(state: axum::extract::State<AppState>, req: Request, next: Next) -> Response {
    let base_url = match state.mastodon_api_url.as_deref() {
        Some(url) => url.to_string(),
        None => return next.run(req).await,
    };

    let method = req.method().clone();
    let path = req.uri().path_and_query().map(ToString::to_string);
    let headers = req.headers().clone();

    if method != Method::GET {
        let Some(path) = path else {
            return next.run(req).await;
        };
        let body = axum::body::to_bytes(req.into_body(), 1_048_576).await.ok();
        return proxy(&base_url, &path, &method, &headers, body.as_deref()).await;
    }

    let response = next.run(req).await;

    if response.status() != StatusCode::NOT_FOUND {
        return response;
    }

    let Some(path) = path else {
        return response;
    };

    proxy(&base_url, &path, &method, &headers, None).await
}

async fn proxy(
    base_url: &str,
    path: &str,
    method: &Method,
    headers: &HeaderMap,
    body: Option<&[u8]>,
) -> Response {
    let url = format!("{base_url}{path}");

    let mut req = HTTP_CLIENT.request(method.clone(), &url);

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
