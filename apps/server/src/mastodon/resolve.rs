use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use axum::http::{StatusCode, header};
use futures::FutureExt;
use futures::future::{BoxFuture, Shared};
use serde::Deserialize;
use sqlx::PgPool;

use crate::auth::BearerToken;

const SEARCH_TIMEOUT: Duration = Duration::from_secs(8);

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ResolveError {
    Unreachable,
    NotFound,
    Blocked,
    Forbidden,
    RateLimited { retry_after: Option<Duration> },
    Upstream(StatusCode),
    Db,
}

impl ResolveError {
    #[must_use]
    pub fn metric_outcome(&self) -> &'static str {
        match self {
            Self::Unreachable => "unreachable",
            Self::NotFound => "not_found",
            Self::Blocked => "blocked",
            Self::Forbidden => "forbidden",
            Self::RateLimited { .. } => "rate_limited",
            Self::Upstream(_) => "upstream",
            Self::Db => "db",
        }
    }
}

type FlightFuture = Shared<BoxFuture<'static, Result<i64, ResolveError>>>;

pub struct Resolver {
    pool: PgPool,
    http: reqwest::Client,
    mastodon_base: Option<Arc<str>>,
    flights: Mutex<HashMap<i64, FlightFuture>>,
}

impl Resolver {
    #[must_use]
    pub fn new(pool: PgPool, http: reqwest::Client, mastodon_base: Option<String>) -> Arc<Self> {
        Arc::new(Self {
            pool,
            http,
            mastodon_base: mastodon_base.map(Arc::from),
            flights: Mutex::new(HashMap::new()),
        })
    }

    /// Returns the Mastodon local id for a Fediway snowflake, resolving via
    /// [`/api/v2/search?resolve=true`](https://docs.joinmastodon.org/methods/search/#v2)
    /// on first call and caching the mapping in `commonfeed_statuses.mastodon_local_id`.
    ///
    /// Concurrent callers for the same snowflake share a single in-flight
    /// search request — the first caller drives the fetch, subsequent callers
    /// await the same future.
    pub async fn resolve(
        self: &Arc<Self>,
        snowflake: i64,
        token: &BearerToken,
    ) -> Result<i64, ResolveError> {
        match state::statuses::find_by_id(&self.pool, snowflake).await {
            Ok(Some(row)) => {
                if let Some(id) = row.mastodon_local_id {
                    metrics::counter!("fediway_resolve_total", "outcome" => "hit").increment(1);
                    return Ok(id);
                }
            }
            Ok(None) => {
                metrics::counter!("fediway_resolve_total", "outcome" => "not_found").increment(1);
                return Err(ResolveError::NotFound);
            }
            Err(e) => {
                tracing::warn!(error = %e, snowflake, "resolver: db lookup failed");
                metrics::counter!("fediway_resolve_total", "outcome" => "db").increment(1);
                return Err(ResolveError::Db);
            }
        }

        let shared = {
            let mut flights = self.flights.lock().expect("resolver flight map poisoned");
            if let Some(existing) = flights.get(&snowflake) {
                existing.clone()
            } else {
                let this = Arc::clone(self);
                let token = token.clone();
                let fut = async move { this.drive_search(snowflake, token).await }
                    .boxed()
                    .shared();
                flights.insert(snowflake, fut.clone());
                fut
            }
        };

        let result = shared.await;
        self.flights
            .lock()
            .expect("resolver flight map poisoned")
            .remove(&snowflake);

        let outcome = match &result {
            Ok(_) => "resolved",
            Err(e) => e.metric_outcome(),
        };
        metrics::counter!("fediway_resolve_total", "outcome" => outcome).increment(1);

        result
    }

    async fn drive_search(&self, snowflake: i64, token: BearerToken) -> Result<i64, ResolveError> {
        let Some(base) = self.mastodon_base.as_deref() else {
            return Err(ResolveError::Unreachable);
        };

        let row = match state::statuses::find_by_id(&self.pool, snowflake).await {
            Ok(Some(r)) => r,
            Ok(None) => return Err(ResolveError::NotFound),
            Err(e) => {
                tracing::warn!(error = %e, snowflake, "resolver: db lookup failed");
                return Err(ResolveError::Db);
            }
        };

        if let Some(id) = row.mastodon_local_id {
            return Ok(id);
        }

        if row.post_uri.is_empty() {
            return Err(ResolveError::NotFound);
        }

        let url = format!("{base}/api/v2/search");
        let resp = match self
            .http
            .get(&url)
            .bearer_auth(token.as_str())
            .query(&[
                ("q", row.post_uri.as_str()),
                ("resolve", "true"),
                ("type", "statuses"),
                ("limit", "1"),
            ])
            .timeout(SEARCH_TIMEOUT)
            .send()
            .await
        {
            Ok(r) => r,
            Err(e) => {
                tracing::warn!(error = %e, snowflake, "resolver: search request failed");
                return Err(ResolveError::Unreachable);
            }
        };

        let status = resp.status();
        if !status.is_success() {
            return Err(match status.as_u16() {
                401 | 403 => ResolveError::Forbidden,
                422 => ResolveError::Blocked,
                429 => {
                    let retry_after = resp
                        .headers()
                        .get(header::RETRY_AFTER)
                        .and_then(|v| v.to_str().ok())
                        .and_then(|s| s.parse::<u64>().ok())
                        .map(Duration::from_secs);
                    ResolveError::RateLimited { retry_after }
                }
                code => ResolveError::Upstream(
                    StatusCode::from_u16(code).unwrap_or(StatusCode::BAD_GATEWAY),
                ),
            });
        }

        let body = match resp.json::<SearchResponse>().await {
            Ok(b) => b,
            Err(e) => {
                tracing::warn!(error = %e, snowflake, "resolver: failed to parse search response");
                return Err(ResolveError::Upstream(StatusCode::BAD_GATEWAY));
            }
        };

        let Some(first) = body.statuses.into_iter().next() else {
            return Err(ResolveError::Forbidden);
        };

        let mastodon_local_id: i64 = match first.id.parse() {
            Ok(id) => id,
            Err(e) => {
                tracing::warn!(
                    error = %e,
                    snowflake,
                    id = first.id,
                    "resolver: non-numeric mastodon id"
                );
                return Err(ResolveError::Upstream(StatusCode::BAD_GATEWAY));
            }
        };

        if let Err(e) =
            state::statuses::set_mastodon_local_id(&self.pool, snowflake, mastodon_local_id).await
        {
            tracing::warn!(error = %e, snowflake, "resolver: failed to persist mapping");
            return Err(ResolveError::Db);
        }

        Ok(mastodon_local_id)
    }
}

#[derive(Deserialize)]
struct SearchResponse {
    statuses: Vec<SearchStatus>,
}

#[derive(Deserialize)]
struct SearchStatus {
    id: String,
}
