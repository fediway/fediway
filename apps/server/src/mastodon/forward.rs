use std::error::Error;

use axum::body::{Body, Bytes};
use axum::http::{HeaderMap, HeaderValue, Method, StatusCode, header};
use axum::response::{IntoResponse, Response};

#[derive(Debug)]
pub struct ForwardError;

pub struct ForwardResponse {
    pub status: StatusCode,
    pub body: Bytes,
    pub content_type: Option<HeaderValue>,
}

impl IntoResponse for ForwardResponse {
    fn into_response(self) -> Response {
        let mut resp = (self.status, Body::from(self.body)).into_response();
        if let Some(ct) = self.content_type {
            resp.headers_mut().insert(header::CONTENT_TYPE, ct);
        }
        resp
    }
}

/// Issues an HTTP request to Mastodon and returns the raw response.
///
/// Mastodon-side 4xx/5xx responses are returned as `Ok` with the upstream
/// status and body so handlers can choose to pass them through or rewrite.
/// Only transport-level failures (DNS, connect, timeout, body read) produce
/// [`ForwardError`].
pub async fn forward(
    http: &reqwest::Client,
    base_url: &str,
    method: Method,
    path: &str,
    headers: &HeaderMap,
    body: Option<Bytes>,
) -> Result<ForwardResponse, ForwardError> {
    let url = format!("{base_url}{path}");
    let mut req = http.request(method.clone(), &url);

    for (name, value) in headers {
        req = req.header(name, value);
    }

    if let Some(bytes) = body {
        req = req.body(bytes.to_vec());
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
                "mastodon forward failed"
            );
            return Err(ForwardError);
        }
    };

    let status = StatusCode::from_u16(resp.status().as_u16()).unwrap_or(StatusCode::BAD_GATEWAY);
    let content_type = resp.headers().get(header::CONTENT_TYPE).cloned();
    let body = match resp.bytes().await {
        Ok(b) => b,
        Err(e) => {
            tracing::warn!(error = %e, url, "mastodon forward response read failed");
            return Err(ForwardError);
        }
    };

    Ok(ForwardResponse {
        status,
        body,
        content_type,
    })
}
