use common::types::Provider;
use sqlx::PgPool;

pub async fn find_for_capability(db: &PgPool, resource: &str, algorithm: &str) -> Vec<Provider> {
    let rows = sqlx::query_as::<_, ProviderRow>(
        "SELECT p.base_url, p.api_key, p.max_results, c.filters
         FROM commonfeed_providers p
         JOIN commonfeed_capabilities c ON c.provider_domain = p.domain
         WHERE p.status = 'approved' AND p.enabled = true
           AND c.resource = $1 AND c.algorithm = $2 AND c.enabled = true",
    )
    .bind(resource)
    .bind(algorithm)
    .fetch_all(db)
    .await
    .unwrap_or_default();

    rows.into_iter()
        .map(|r| Provider {
            base_url: r.base_url,
            api_key: r.api_key,
            max_results: usize::try_from(r.max_results).unwrap_or(100),
            supported_filters: r.filters,
        })
        .collect()
}

#[derive(sqlx::FromRow)]
struct ProviderRow {
    base_url: String,
    api_key: String,
    max_results: i32,
    filters: Vec<String>,
}
