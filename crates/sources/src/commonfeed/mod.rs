pub mod links;
pub mod posts;
pub mod tags;
pub mod types;

use common::types::Provider;
use reqwest::Client;
use serde::de::DeserializeOwned;

use types::QueryFilters;

/// Fetch JSON from a `CommonFeed` provider endpoint.
///
/// Handles filter application, bearer auth, and error logging.
/// Returns `None` on any failure (network, HTTP error, parse error).
pub(crate) async fn fetch_json<T: DeserializeOwned>(
    provider: &Provider,
    resource: &str,
    algorithm: &str,
    filters: &QueryFilters,
    limit: usize,
) -> Option<T> {
    let client = Client::new();
    let url = format!("{}/{resource}/{algorithm}", provider.base_url);
    let request_limit = limit.min(provider.max_results);

    let mut body = serde_json::json!({
        "limit": request_limit,
        "cursor": null
    });

    let supported = &provider.supported_filters;
    let filters = filters.for_provider(supported);
    let filters = serde_json::to_value(&filters).unwrap_or_default();
    if filters.as_object().is_some_and(|m| !m.is_empty()) {
        body["filters"] = filters;
    }

    let resp = match client
        .post(&url)
        .bearer_auth(&provider.api_key)
        .json(&body)
        .send()
        .await
    {
        Ok(r) => r,
        Err(e) => {
            tracing::warn!(url = %url, error = %e, "provider request failed");
            return None;
        }
    };

    if !resp.status().is_success() {
        tracing::warn!(url = %url, status = %resp.status(), "provider returned error");
        return None;
    }

    match resp.json::<T>().await {
        Ok(r) => Some(r),
        Err(e) => {
            tracing::warn!(url = %url, error = %e, "failed to parse provider response");
            None
        }
    }
}
