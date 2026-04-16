use std::future::Future;
use std::pin::Pin;
use std::time::{Duration, Instant};

use axum::Json;
use axum::http::{HeaderMap, HeaderValue, header};
use feed::Feed;
use serde::Serialize;
use serde::de::DeserializeOwned;

use crate::feeds::engine;
use crate::state::AppState;

const TTL: Duration = Duration::from_secs(60);

pub trait TrendFeed: Feed + Send {
    type Response: Serialize + Send;

    const RESOURCE: &'static str;
    const PATH: &'static str;

    fn cache_key(&self) -> String;

    fn map(
        &self,
        state: &AppState,
        items: Vec<Self::Item>,
    ) -> impl Future<Output = Vec<Self::Response>> + Send;

    fn rebuild(&self, state: &AppState) -> Pin<Box<dyn Future<Output = Vec<Self::Item>> + Send>>;
}

pub async fn serve<F>(
    state: &AppState,
    feed: &F,
    cursor: Option<&str>,
    limit: usize,
) -> (HeaderMap, Json<Vec<F::Response>>)
where
    F: TrendFeed,
    F::Item: Serialize + DeserializeOwned,
{
    let start = Instant::now();
    metrics::counter!("fediway_trends_requests_total", "resource" => F::RESOURCE).increment(1);

    let key = feed.cache_key();
    let (items, from_cache) = if let Some(cached) = state.cache.get::<Vec<F::Item>>(&key).await {
        (cached, true)
    } else {
        let fresh: Vec<F::Item> = feed.collect().await.into_iter().map(|c| c.item).collect();
        state.cache.set(&key, &fresh, TTL).await;
        (fresh, false)
    };

    if from_cache {
        let cache = state.cache.clone();
        let key = key.clone();
        let rebuild = feed.rebuild(state);
        tokio::spawn(async move {
            let items = rebuild.await;
            cache.set(&key, &items, TTL).await;
        });
    }

    let page = engine::paginate(items, cursor, limit);
    let next_cursor = page.cursor;
    let mapped = feed.map(state, page.items).await;

    #[allow(clippy::cast_precision_loss)]
    metrics::histogram!("fediway_trends_results", "resource" => F::RESOURCE)
        .record(mapped.len() as f64);

    let mut headers = HeaderMap::new();
    if let Some(c) = &next_cursor {
        let link = format!(
            "<https://{}{}?offset={c}>; rel=\"next\"",
            state.instance_domain,
            F::PATH
        );
        if let Ok(value) = HeaderValue::from_str(&link) {
            headers.insert(header::LINK, value);
        }
    }

    metrics::histogram!("fediway_trends_duration_seconds", "resource" => F::RESOURCE)
        .record(start.elapsed().as_secs_f64());

    (headers, Json(mapped))
}
