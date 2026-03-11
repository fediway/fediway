use common::types::Provider;
use sqlx::PgPool;

/// Find sources configured for a fediway route.
pub async fn find_sources(db: &PgPool, route: &str) -> Vec<BoundProvider> {
    let rows = sqlx::query_as::<_, BoundProviderRow>(
        "SELECT p.domain, p.base_url, p.api_key, p.max_results, c.filters, b.algorithm
         FROM commonfeed_sources b
         JOIN commonfeed_providers p ON p.domain = b.provider_domain
         JOIN commonfeed_capabilities c ON c.provider_domain = b.provider_domain
              AND c.resource = b.resource AND c.algorithm = b.algorithm
         WHERE b.route = $1 AND b.enabled = true
           AND p.status = 'approved' AND p.enabled = true",
    )
    .bind(route)
    .fetch_all(db)
    .await
    .unwrap_or_else(|e| {
        tracing::warn!(error = %e, "failed to query sources");
        Vec::new()
    });

    rows.into_iter()
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
        .collect()
}

pub async fn upsert(
    db: &PgPool,
    domain: &str,
    name: &str,
    base_url: &str,
    max_results: i32,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "INSERT INTO commonfeed_providers (domain, name, base_url, max_results)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (domain) DO UPDATE SET
             name = EXCLUDED.name,
             base_url = EXCLUDED.base_url,
             max_results = EXCLUDED.max_results,
             updated_at = now()",
    )
    .bind(domain)
    .bind(name)
    .bind(base_url)
    .bind(max_results)
    .execute(db)
    .await?;
    Ok(())
}

pub async fn upsert_capability(
    db: &PgPool,
    provider_domain: &str,
    resource: &str,
    algorithm: &str,
    description: &str,
    filters: &[String],
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "INSERT INTO commonfeed_capabilities (provider_domain, resource, algorithm, description, filters)
         VALUES ($1, $2, $3, $4, $5)
         ON CONFLICT (provider_domain, resource, algorithm) DO UPDATE SET
             description = EXCLUDED.description,
             filters = EXCLUDED.filters",
    )
    .bind(provider_domain)
    .bind(resource)
    .bind(algorithm)
    .bind(description)
    .bind(filters)
    .execute(db)
    .await?;
    Ok(())
}

pub async fn find_base_url(db: &PgPool, domain: &str) -> Result<Option<String>, sqlx::Error> {
    sqlx::query_scalar::<_, String>("SELECT base_url FROM commonfeed_providers WHERE domain = $1")
        .bind(domain)
        .fetch_optional(db)
        .await
}

pub async fn save_registration(
    db: &PgPool,
    domain: &str,
    api_key: &str,
    request_id: &str,
    status: &str,
    verify_path: &str,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "UPDATE commonfeed_providers
         SET api_key = $1, request_id = $2, status = $3, verify_path = $4, updated_at = now()
         WHERE domain = $5",
    )
    .bind(api_key)
    .bind(request_id)
    .bind(status)
    .bind(verify_path)
    .bind(domain)
    .execute(db)
    .await?;
    Ok(())
}

pub async fn find_registration(
    db: &PgPool,
    domain: &str,
) -> Result<Option<(Option<String>, Option<String>)>, sqlx::Error> {
    sqlx::query_as::<_, (Option<String>, Option<String>)>(
        "SELECT api_key, status FROM commonfeed_providers WHERE domain = $1",
    )
    .bind(domain)
    .fetch_optional(db)
    .await
}

pub async fn update_status(db: &PgPool, domain: &str, status: &str) -> Result<(), sqlx::Error> {
    sqlx::query(
        "UPDATE commonfeed_providers SET status = $1, updated_at = now() WHERE domain = $2",
    )
    .bind(status)
    .bind(domain)
    .execute(db)
    .await?;
    Ok(())
}

/// Enable a provider capability as a source for a fediway route.
pub async fn enable_source(
    db: &PgPool,
    route: &str,
    provider_domain: &str,
    resource: &str,
    algorithm: &str,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "INSERT INTO commonfeed_sources (route, provider_domain, resource, algorithm)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (route, provider_domain) DO UPDATE SET
             resource = EXCLUDED.resource,
             algorithm = EXCLUDED.algorithm,
             enabled = true",
    )
    .bind(route)
    .bind(provider_domain)
    .bind(resource)
    .bind(algorithm)
    .execute(db)
    .await?;
    Ok(())
}

/// Disable a source for a fediway route.
pub async fn disable_source(
    db: &PgPool,
    route: &str,
    provider_domain: &str,
) -> Result<u64, sqlx::Error> {
    let result = sqlx::query(
        "UPDATE commonfeed_sources SET enabled = false
         WHERE route = $1 AND provider_domain = $2",
    )
    .bind(route)
    .bind(provider_domain)
    .execute(db)
    .await?;
    Ok(result.rows_affected())
}

/// A provider bound to a route, including which algorithm to call.
pub struct BoundProvider {
    pub provider: Provider,
    pub algorithm: String,
}

#[derive(sqlx::FromRow)]
struct BoundProviderRow {
    domain: String,
    base_url: String,
    api_key: String,
    max_results: i32,
    filters: Vec<String>,
    algorithm: String,
}
