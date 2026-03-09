use anyhow::Result;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct WellKnown {
    name: String,
    domain: String,
    version: String,
    base_url: String,
    capabilities: Vec<CapabilityDef>,
    max_results: i32,
    rate_limits: Option<RateLimits>,
    contact: Option<String>,
}

#[derive(Deserialize)]
struct CapabilityDef {
    resource: String,
    algorithm: String,
    description: String,
    filters: Vec<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct RateLimits {
    requests_per_hour: u32,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct RegisterRequest {
    domain: String,
    name: String,
    callback_url: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct RegisterResponse {
    request_id: String,
    status: String,
    api_key: String,
    verify_path: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct StatusResponse {
    status: String,
    message: Option<String>,
}

async fn fetch_well_known(domain: &str) -> Result<WellKnown> {
    let url = format!("https://{domain}/.well-known/commonfeed");
    let wk = reqwest::get(&url)
        .await?
        .error_for_status()?
        .json::<WellKnown>()
        .await?;
    Ok(wk)
}

fn print_well_known(wk: &WellKnown) {
    println!("{} ({})", wk.name, wk.domain);
    println!("Spec version: {}", wk.version);
    println!("Base URL:     {}", wk.base_url);

    println!("\nCapabilities:");
    for cap in &wk.capabilities {
        println!("  {}/{} — {}", cap.resource, cap.algorithm, cap.description);
        if !cap.filters.is_empty() {
            println!("    filters: {}", cap.filters.join(", "));
        }
    }

    println!("\nMax results: {}", wk.max_results);

    if let Some(limits) = &wk.rate_limits {
        println!("Rate limit:  {} req/hr", limits.requests_per_hour);
    }

    if let Some(contact) = &wk.contact {
        println!("Contact:     {contact}");
    }
}

pub async fn info(domain: &str) -> Result<()> {
    let wk = fetch_well_known(domain).await?;
    print_well_known(&wk);
    Ok(())
}

pub async fn add(db: &PgPool, domain: &str) -> Result<()> {
    let wk = fetch_well_known(domain).await?;

    sqlx::query(
        "INSERT INTO commonfeed_providers (domain, name, base_url, max_results)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (domain) DO UPDATE SET
             name = EXCLUDED.name,
             base_url = EXCLUDED.base_url,
             max_results = EXCLUDED.max_results,
             updated_at = now()",
    )
    .bind(&wk.domain)
    .bind(&wk.name)
    .bind(&wk.base_url)
    .bind(wk.max_results)
    .execute(db)
    .await?;

    for cap in &wk.capabilities {
        sqlx::query(
            "INSERT INTO commonfeed_capabilities (provider_domain, resource, algorithm, description, filters)
             VALUES ($1, $2, $3, $4, $5)
             ON CONFLICT (provider_domain, resource, algorithm) DO UPDATE SET
                 description = EXCLUDED.description,
                 filters = EXCLUDED.filters"
        )
        .bind(&wk.domain)
        .bind(&cap.resource)
        .bind(&cap.algorithm)
        .bind(&cap.description)
        .bind(&cap.filters)
        .execute(db)
        .await?;
    }

    print_well_known(&wk);
    println!("\nProvider added.");

    Ok(())
}

pub async fn register(
    db: &PgPool,
    domain: &str,
    instance_domain: &str,
    instance_name: &str,
) -> Result<()> {
    let base_url = sqlx::query_scalar::<_, String>(
        "SELECT base_url FROM commonfeed_providers WHERE domain = $1",
    )
    .bind(domain)
    .fetch_optional(db)
    .await?;

    let Some(base_url) = base_url else {
        anyhow::bail!("Provider not found. Run `provider add {domain}` first.");
    };

    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{base_url}/register"))
        .json(&RegisterRequest {
            domain: instance_domain.to_string(),
            name: instance_name.to_string(),
            callback_url: format!("https://{instance_domain}/commonfeed/callback"),
        })
        .send()
        .await?
        .error_for_status()?
        .json::<RegisterResponse>()
        .await?;

    sqlx::query(
        "UPDATE commonfeed_providers
         SET api_key = $1, request_id = $2, status = $3, verify_path = $4, updated_at = now()
         WHERE domain = $5",
    )
    .bind(&resp.api_key)
    .bind(&resp.request_id)
    .bind(&resp.status)
    .bind(&resp.verify_path)
    .bind(domain)
    .execute(db)
    .await?;

    println!("Registration submitted!");
    println!("  Status:      {}", resp.status);
    println!("  Verify path: {}", resp.verify_path);
    println!("\nThe provider will verify your domain. Check status with:");
    println!("  fediway-cli provider status {domain}");

    Ok(())
}

pub async fn status(db: &PgPool, domain: &str) -> Result<()> {
    let row = sqlx::query_as::<_, (Option<String>, Option<String>)>(
        "SELECT api_key, status FROM commonfeed_providers WHERE domain = $1",
    )
    .bind(domain)
    .fetch_optional(db)
    .await?;

    let Some((api_key, current_status)) = row else {
        anyhow::bail!("Provider not found. Run `provider add {domain}` first.");
    };

    if current_status.as_deref() == Some("approved") {
        println!("Already approved.");
        return Ok(());
    }

    let Some(api_key) = api_key else {
        anyhow::bail!("Not registered yet. Run `provider register {domain}` first.");
    };

    let base_url = sqlx::query_scalar::<_, String>(
        "SELECT base_url FROM commonfeed_providers WHERE domain = $1",
    )
    .bind(domain)
    .fetch_one(db)
    .await?;

    let client = reqwest::Client::new();
    let resp = client
        .get(format!("{base_url}/register/status"))
        .bearer_auth(&api_key)
        .send()
        .await?
        .error_for_status()?
        .json::<StatusResponse>()
        .await?;

    sqlx::query(
        "UPDATE commonfeed_providers SET status = $1, updated_at = now() WHERE domain = $2",
    )
    .bind(&resp.status)
    .bind(domain)
    .execute(db)
    .await?;

    println!("Status: {}", resp.status);
    if let Some(msg) = &resp.message {
        println!("Message: {msg}");
    }

    Ok(())
}

pub async fn enable(db: &PgPool, domain: &str, capability: &str) -> Result<()> {
    let (resource, algorithm) = parse_capability(capability)?;

    let rows = sqlx::query(
        "UPDATE commonfeed_capabilities SET enabled = true
         WHERE provider_domain = $1 AND resource = $2 AND algorithm = $3",
    )
    .bind(domain)
    .bind(resource)
    .bind(algorithm)
    .execute(db)
    .await?
    .rows_affected();

    if rows == 0 {
        anyhow::bail!("Capability '{capability}' not found for provider '{domain}'.");
    }

    println!("Enabled {capability} for {domain}.");
    Ok(())
}

pub async fn disable(db: &PgPool, domain: &str, capability: &str) -> Result<()> {
    let (resource, algorithm) = parse_capability(capability)?;

    let rows = sqlx::query(
        "UPDATE commonfeed_capabilities SET enabled = false
         WHERE provider_domain = $1 AND resource = $2 AND algorithm = $3",
    )
    .bind(domain)
    .bind(resource)
    .bind(algorithm)
    .execute(db)
    .await?
    .rows_affected();

    if rows == 0 {
        anyhow::bail!("Capability '{capability}' not found for provider '{domain}'.");
    }

    println!("Disabled {capability} for {domain}.");
    Ok(())
}

fn parse_capability(capability: &str) -> Result<(&str, &str)> {
    capability.split_once('/').ok_or_else(|| {
        anyhow::anyhow!("Capability must be in format 'resource/algorithm' (e.g. posts/trending)")
    })
}
