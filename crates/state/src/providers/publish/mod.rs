use serde_json::Value;
use sqlx::{Executor, Postgres};

#[tracing::instrument(
    skip(e),
    name = "db.providers.publish.upsert",
    fields(domain = %domain),
)]
pub async fn upsert(
    e: impl Executor<'_, Database = Postgres>,
    domain: &str,
    name: &str,
    base_url: &str,
    max_results: i32,
) -> Result<(), crate::Error> {
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
    .execute(e)
    .await?;
    Ok(())
}

pub struct Capability<'a> {
    pub provider_domain: &'a str,
    pub resource: &'a str,
    pub algorithm: &'a str,
    pub description: &'a str,
    pub filters: &'a [String],
    pub embedding_required: Option<bool>,
    pub embedding_models: Option<Value>,
}

#[tracing::instrument(
    skip(e, cap),
    name = "db.providers.publish.upsert_capability",
    fields(domain = %cap.provider_domain, resource = %cap.resource, algorithm = %cap.algorithm),
)]
pub async fn upsert_capability(
    e: impl Executor<'_, Database = Postgres>,
    cap: &Capability<'_>,
) -> Result<(), crate::Error> {
    sqlx::query(
        "INSERT INTO commonfeed_capabilities
         (provider_domain, resource, algorithm, description, filters,
          embedding_required, embedding_models)
         VALUES ($1, $2, $3, $4, $5, $6, $7)
         ON CONFLICT (provider_domain, resource, algorithm) DO UPDATE SET
             description = EXCLUDED.description,
             filters = EXCLUDED.filters,
             embedding_required = EXCLUDED.embedding_required,
             embedding_models = EXCLUDED.embedding_models",
    )
    .bind(cap.provider_domain)
    .bind(cap.resource)
    .bind(cap.algorithm)
    .bind(cap.description)
    .bind(cap.filters)
    .bind(cap.embedding_required)
    .bind(&cap.embedding_models)
    .execute(e)
    .await?;
    Ok(())
}

#[tracing::instrument(
    skip(e, api_key, request_id, verify_path),
    name = "db.providers.publish.save_registration",
    fields(domain = %domain, status = %status),
)]
pub async fn save_registration(
    e: impl Executor<'_, Database = Postgres>,
    domain: &str,
    api_key: &str,
    request_id: &str,
    status: &str,
    verify_path: &str,
) -> Result<(), crate::Error> {
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
    .execute(e)
    .await?;
    Ok(())
}

#[tracing::instrument(
    skip(e),
    name = "db.providers.publish.update_status",
    fields(domain = %domain, status = %status),
)]
pub async fn update_status(
    e: impl Executor<'_, Database = Postgres>,
    domain: &str,
    status: &str,
) -> Result<(), crate::Error> {
    sqlx::query(
        "UPDATE commonfeed_providers SET status = $1, updated_at = now() WHERE domain = $2",
    )
    .bind(status)
    .bind(domain)
    .execute(e)
    .await?;
    Ok(())
}

/// Enable a provider capability as a source for a fediway route.
#[tracing::instrument(
    skip(e),
    name = "db.providers.publish.enable_source",
    fields(route = %route, domain = %provider_domain, resource = %resource, algorithm = %algorithm),
)]
pub async fn enable_source(
    e: impl Executor<'_, Database = Postgres>,
    route: &str,
    provider_domain: &str,
    resource: &str,
    algorithm: &str,
) -> Result<(), crate::Error> {
    sqlx::query(
        "INSERT INTO commonfeed_sources (route, provider_domain, resource, algorithm)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (route, provider_domain, algorithm) DO UPDATE SET
             enabled = true",
    )
    .bind(route)
    .bind(provider_domain)
    .bind(resource)
    .bind(algorithm)
    .execute(e)
    .await?;
    Ok(())
}

/// Disable a source for a fediway route.
#[tracing::instrument(
    skip(e),
    name = "db.providers.publish.disable_source",
    fields(route = %route, domain = %provider_domain, algorithm = %algorithm),
)]
pub async fn disable_source(
    e: impl Executor<'_, Database = Postgres>,
    route: &str,
    provider_domain: &str,
    algorithm: &str,
) -> Result<u64, crate::Error> {
    let result = sqlx::query(
        "UPDATE commonfeed_sources SET enabled = false
         WHERE route = $1 AND provider_domain = $2 AND algorithm = $3",
    )
    .bind(route)
    .bind(provider_domain)
    .bind(algorithm)
    .execute(e)
    .await?;
    Ok(result.rows_affected())
}
