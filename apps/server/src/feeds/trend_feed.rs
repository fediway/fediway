use std::time::Instant;

use axum::Json;
use axum::http::{HeaderMap, HeaderValue, header};
use feed::Feed;
use feed::cursor::{Cursor, Offset};

use crate::state::AppState;

/// Supertrait for the three `/api/v1/trends/*` endpoints.
///
/// Bundles the shared serve lifecycle as a default method so trends
/// handlers collapse to "construct feed + delegate". Timeline endpoints
/// (`home`, `tag`, `link`) use Mastodon keyset pagination instead and
/// are not served by this trait.
pub trait TrendFeed: Feed {
    type Response: serde::Serialize + Send;

    const RESOURCE: &'static str;
    const PATH: &'static str;

    fn map(
        &self,
        state: &AppState,
        items: Vec<Self::Item>,
    ) -> impl std::future::Future<Output = Vec<Self::Response>> + Send;

    fn serve(
        &self,
        state: &AppState,
        cursor: Option<&str>,
        limit: usize,
    ) -> impl std::future::Future<Output = (HeaderMap, Json<Vec<Self::Response>>)> + Send {
        async move {
            let start = Instant::now();
            metrics::counter!("fediway_trends_requests_total", "resource" => Self::RESOURCE)
                .increment(1);

            let candidates = self.collect().await;
            let page = Offset::parse(cursor).paginate(candidates, limit);
            let items: Vec<Self::Item> = page.items.into_iter().map(|c| c.item).collect();
            let mapped = self.map(state, items).await;

            #[allow(clippy::cast_precision_loss)]
            metrics::histogram!("fediway_trends_results", "resource" => Self::RESOURCE)
                .record(mapped.len() as f64);

            let mut headers = HeaderMap::new();
            if let Some((key, value)) =
                link_header(&state.instance_domain, Self::PATH, page.cursor.as_ref())
            {
                headers.insert(key, value);
            }

            metrics::histogram!("fediway_trends_duration_seconds", "resource" => Self::RESOURCE)
                .record(start.elapsed().as_secs_f64());

            (headers, Json(mapped))
        }
    }
}

fn link_header(
    domain: &str,
    path: &str,
    cursor: Option<&String>,
) -> Option<(header::HeaderName, HeaderValue)> {
    let cursor = cursor?;
    let value = format!("<https://{domain}{path}?offset={cursor}>; rel=\"next\"");
    HeaderValue::from_str(&value)
        .ok()
        .map(|v| (header::LINK, v))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn link_header_returns_absolute_url() {
        let cursor = Some("abc123".to_string());
        let (key, value) = link_header(
            "mastodon.social",
            "/api/v1/trends/statuses",
            cursor.as_ref(),
        )
        .unwrap();
        assert_eq!(key, header::LINK);
        assert_eq!(
            value.to_str().unwrap(),
            r#"<https://mastodon.social/api/v1/trends/statuses?offset=abc123>; rel="next""#,
        );
    }

    #[test]
    fn link_header_returns_none_without_cursor() {
        assert!(link_header("mastodon.social", "/api/v1/trends/statuses", None).is_none());
    }
}
