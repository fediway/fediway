use common::types::Provider;
use sqlx::{Executor, Postgres};

use super::BoundProvider;
use super::row::BoundProviderRow;
use super::sql::SOURCES_QUERY;

/// Find sources configured for a fediway route.
#[tracing::instrument(
    skip(e),
    name = "db.providers.sources.find_sources",
    fields(route = %route),
)]
pub async fn find_sources(
    e: impl Executor<'_, Database = Postgres>,
    route: &str,
) -> Result<Vec<BoundProvider>, crate::Error> {
    let rows = sqlx::query_as::<_, BoundProviderRow>(SOURCES_QUERY)
        .bind(route)
        .fetch_all(e)
        .await?;

    Ok(rows
        .into_iter()
        .map(|r| BoundProvider {
            provider: Provider {
                domain: r.domain,
                base_url: r.base_url,
                api_key: r.api_key,
                max_results: usize::try_from(r.max_results).unwrap_or(100),
                supported_filters: r.filters,
            },
            algorithm: r.algorithm,
        })
        .collect())
}
