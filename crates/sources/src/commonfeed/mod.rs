pub mod links;
pub mod posts;
pub mod recommended;
pub mod tags;
pub mod types;

use std::sync::LazyLock;
use std::time::{Duration, Instant};

use common::types::Provider;
use reqwest::Client;
use serde::de::DeserializeOwned;

use crate::observe;
use types::{EmbeddingRequest, QueryFilters};

static HTTP_CLIENT: LazyLock<Client> = LazyLock::new(|| {
    Client::builder()
        .timeout(Duration::from_secs(10))
        .connect_timeout(Duration::from_secs(5))
        .redirect(reqwest::redirect::Policy::limited(3))
        .build()
        .expect("http client")
});

/// Fetch JSON from a `CommonFeed` provider endpoint.
///
/// Handles filter application, bearer auth, and error logging.
/// Returns `None` on any failure (network, HTTP error, parse error).
pub(crate) async fn fetch_json<T: DeserializeOwned>(
    provider: &Provider,
    resource: &str,
    algorithm: &str,
    filters: &QueryFilters,
    embedding: Option<&EmbeddingRequest>,
    limit: usize,
) -> Option<T> {
    let url = format!("{}/{resource}/{algorithm}", provider.base_url);
    let request_limit = limit.min(provider.max_results);

    let mut body = serde_json::json!({
        "limit": request_limit,
        "cursor": null
    });

    if let Some(emb) = embedding {
        body["embedding"] = serde_json::to_value(emb).unwrap_or_default();
    }

    let supported = &provider.supported_filters;
    let filters = filters.for_provider(supported);
    let filters = serde_json::to_value(&filters).unwrap_or_default();
    if filters.as_object().is_some_and(|m| !m.is_empty()) {
        body["filters"] = filters;
    }

    let start = Instant::now();

    let resp = match HTTP_CLIENT
        .post(&url)
        .bearer_auth(&provider.api_key)
        .json(&body)
        .send()
        .await
    {
        Ok(r) => r,
        Err(e) => {
            tracing::warn!(url = %url, error = %e, "provider request failed");
            observe::source_fetched(&provider.domain, "network_error", start.elapsed());
            return None;
        }
    };

    if !resp.status().is_success() {
        let status = resp.status();
        let response_text = resp.text().await.unwrap_or_default();
        let response_text: String = response_text.chars().take(512).collect();

        if status.is_client_error() {
            tracing::error!(
                url = %url,
                status = %status,
                response = %response_text,
                request = %body,
                "provider rejected request — config error, will keep failing until fixed"
            );
            observe::source_fetched(&provider.domain, "client_error", start.elapsed());
        } else {
            tracing::warn!(
                url = %url,
                status = %status,
                response = %response_text,
                "provider returned server error"
            );
            observe::source_fetched(&provider.domain, "server_error", start.elapsed());
        }
        return None;
    }

    match resp.json::<T>().await {
        Ok(r) => {
            observe::source_fetched(&provider.domain, "success", start.elapsed());
            Some(r)
        }
        Err(e) => {
            tracing::warn!(url = %url, error = %e, "failed to parse provider response");
            observe::source_fetched(&provider.domain, "parse_error", start.elapsed());
            None
        }
    }
}
