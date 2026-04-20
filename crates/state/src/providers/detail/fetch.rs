use common::types::Provider;
use sqlx::{Executor, Postgres};

use super::Registration;

/// Find a provider by domain, returning it as a `Provider` for API calls.
#[tracing::instrument(
    skip(e),
    name = "db.providers.detail.find_by_domain",
    fields(domain = %domain),
)]
pub async fn find_by_domain(
    e: impl Executor<'_, Database = Postgres>,
    domain: &str,
) -> Result<Option<Provider>, crate::Error> {
    #[derive(sqlx::FromRow)]
    struct Row {
        domain: String,
        base_url: String,
        api_key: String,
        max_results: i32,
    }

    let row = sqlx::query_as::<_, Row>(
        "SELECT domain, base_url, api_key, max_results
         FROM commonfeed_providers
         WHERE domain = $1 AND status = 'approved' AND enabled = true",
    )
    .bind(domain)
    .fetch_optional(e)
    .await?;

    Ok(row.map(|r| Provider {
        domain: r.domain,
        base_url: r.base_url,
        api_key: r.api_key,
        max_results: usize::try_from(r.max_results).unwrap_or(100),
        supported_filters: Vec::new(),
    }))
}

#[tracing::instrument(
    skip(e),
    name = "db.providers.detail.find_base_url",
    fields(domain = %domain),
)]
pub async fn find_base_url(
    e: impl Executor<'_, Database = Postgres>,
    domain: &str,
) -> Result<Option<String>, crate::Error> {
    Ok(sqlx::query_scalar::<_, String>(
        "SELECT base_url FROM commonfeed_providers WHERE domain = $1",
    )
    .bind(domain)
    .fetch_optional(e)
    .await?)
}

#[tracing::instrument(
    skip(e),
    name = "db.providers.detail.find_registration",
    fields(domain = %domain),
)]
pub async fn find_registration(
    e: impl Executor<'_, Database = Postgres>,
    domain: &str,
) -> Result<Option<Registration>, crate::Error> {
    Ok(sqlx::query_as::<_, Registration>(
        "SELECT api_key, status FROM commonfeed_providers WHERE domain = $1",
    )
    .bind(domain)
    .fetch_optional(e)
    .await?)
}
