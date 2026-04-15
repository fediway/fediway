use std::time::Duration;

use axum::http::{HeaderValue, StatusCode, header};
use axum::response::{IntoResponse, Response};

use crate::mastodon::forward::ForwardError;
use crate::mastodon::resolve::ResolveError;

#[derive(Debug)]
pub enum EngagementError {
    NotFound,
    Unresolvable,
    Forbidden,
    Blocked,
    RateLimited { retry_after: Option<Duration> },
    Upstream(StatusCode),
    Unreachable,
    BadBody,
    Db,
}

impl EngagementError {
    #[must_use]
    pub fn metric_outcome(&self) -> &'static str {
        match self {
            Self::NotFound => "not_found",
            Self::Unresolvable => "unresolvable",
            Self::Forbidden => "forbidden",
            Self::Blocked => "blocked",
            Self::RateLimited { .. } => "rate_limited",
            Self::Upstream(_) => "upstream",
            Self::Unreachable => "unreachable",
            Self::BadBody => "bad_body",
            Self::Db => "db",
        }
    }
}

impl From<ResolveError> for EngagementError {
    fn from(e: ResolveError) -> Self {
        match e {
            ResolveError::NotFound => Self::NotFound,
            ResolveError::Unresolvable => Self::Unresolvable,
            ResolveError::Forbidden => Self::Forbidden,
            ResolveError::Blocked => Self::Blocked,
            ResolveError::Unreachable => Self::Unreachable,
            ResolveError::RateLimited { retry_after } => Self::RateLimited { retry_after },
            ResolveError::Upstream(s) => Self::Upstream(s),
            ResolveError::Db => Self::Db,
        }
    }
}

impl From<ForwardError> for EngagementError {
    fn from(_: ForwardError) -> Self {
        Self::Unreachable
    }
}

impl From<sqlx::Error> for EngagementError {
    fn from(e: sqlx::Error) -> Self {
        tracing::warn!(error = %e, "engagement: db error");
        Self::Db
    }
}

impl From<serde_json::Error> for EngagementError {
    fn from(e: serde_json::Error) -> Self {
        tracing::warn!(error = %e, "engagement: failed to parse mastodon response");
        Self::BadBody
    }
}

impl IntoResponse for EngagementError {
    fn into_response(self) -> Response {
        match self {
            Self::NotFound | Self::Unresolvable => StatusCode::NOT_FOUND.into_response(),
            Self::Forbidden | Self::Blocked => StatusCode::FORBIDDEN.into_response(),
            Self::Unreachable | Self::BadBody => StatusCode::BAD_GATEWAY.into_response(),
            Self::Db => StatusCode::INTERNAL_SERVER_ERROR.into_response(),
            Self::Upstream(s) => s.into_response(),
            Self::RateLimited { retry_after } => {
                let mut resp = StatusCode::TOO_MANY_REQUESTS.into_response();
                if let Some(d) = retry_after
                    && let Ok(v) = HeaderValue::from_str(&d.as_secs().to_string())
                {
                    resp.headers_mut().insert(header::RETRY_AFTER, v);
                }
                resp
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolve_not_found_maps_to_404() {
        let err: EngagementError = ResolveError::NotFound.into();
        assert_eq!(err.into_response().status(), StatusCode::NOT_FOUND);
    }

    #[test]
    fn resolve_forbidden_maps_to_403() {
        let err: EngagementError = ResolveError::Forbidden.into();
        assert_eq!(err.into_response().status(), StatusCode::FORBIDDEN);
    }

    #[test]
    fn resolve_unresolvable_maps_to_404() {
        let err: EngagementError = ResolveError::Unresolvable.into();
        assert_eq!(err.into_response().status(), StatusCode::NOT_FOUND);
    }

    #[test]
    fn resolve_blocked_maps_to_403() {
        let err: EngagementError = ResolveError::Blocked.into();
        assert_eq!(err.into_response().status(), StatusCode::FORBIDDEN);
    }

    #[test]
    fn resolve_unreachable_maps_to_502() {
        let err: EngagementError = ResolveError::Unreachable.into();
        assert_eq!(err.into_response().status(), StatusCode::BAD_GATEWAY);
    }

    #[test]
    fn forward_error_maps_to_502() {
        let err: EngagementError = ForwardError.into();
        assert_eq!(err.into_response().status(), StatusCode::BAD_GATEWAY);
    }

    #[test]
    fn rate_limited_includes_retry_after_header() {
        let err: EngagementError = ResolveError::RateLimited {
            retry_after: Some(Duration::from_secs(42)),
        }
        .into();
        let resp = err.into_response();
        assert_eq!(resp.status(), StatusCode::TOO_MANY_REQUESTS);
        assert_eq!(resp.headers().get(header::RETRY_AFTER).unwrap(), "42");
    }

    #[test]
    fn rate_limited_without_retry_after_still_429() {
        let err: EngagementError = ResolveError::RateLimited { retry_after: None }.into();
        let resp = err.into_response();
        assert_eq!(resp.status(), StatusCode::TOO_MANY_REQUESTS);
        assert!(resp.headers().get(header::RETRY_AFTER).is_none());
    }

    #[test]
    fn upstream_error_passes_through() {
        let err: EngagementError = ResolveError::Upstream(StatusCode::IM_A_TEAPOT).into();
        assert_eq!(err.into_response().status(), StatusCode::IM_A_TEAPOT);
    }
}
