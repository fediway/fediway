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
    let base = if domain.contains("://") {
        domain.to_string()
    } else {
        format!("https://{domain}")
    };
    let url = format!("{base}/.well-known/commonfeed");
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

/// Resolve a provider domain from user input.
///
/// Accepts the stored domain, a base URL, or `host:port` shorthand.
/// Returns the canonical domain as stored in `commonfeed_providers`.
pub async fn resolve_domain(db: &PgPool, input: &str) -> Result<String> {
    // Exact match on domain column.
    if state::providers::find_base_url(db, input).await?.is_some() {
        return Ok(input.to_string());
    }

    // Try matching by base_url (user may pass "localhost:3000" or "http://localhost:3000").
    let candidates: Vec<String> = if input.contains("://") {
        vec![input.trim_end_matches('/').to_string()]
    } else {
        vec![
            format!("https://{}", input.trim_end_matches('/')),
            format!("http://{}", input.trim_end_matches('/')),
        ]
    };

    for candidate in &candidates {
        // Exact base_url match (with or without trailing slash).
        let domain = sqlx::query_scalar::<_, String>(
            "SELECT domain FROM commonfeed_providers
             WHERE RTRIM(base_url, '/') = $1 OR base_url LIKE $1 || '/%'",
        )
        .bind(candidate)
        .fetch_optional(db)
        .await?;

        if let Some(d) = domain {
            return Ok(d);
        }
    }

    anyhow::bail!("Provider '{input}' not found. Run `provider add` or `provider register` first.")
}

pub async fn info(domain: &str) -> Result<()> {
    let wk = fetch_well_known(domain).await?;
    print_well_known(&wk);
    Ok(())
}

pub async fn add(db: &PgPool, domain: &str) -> Result<()> {
    let wk = sync_provider(db, domain).await?;
    print_well_known(&wk);
    println!("\nProvider added.");
    Ok(())
}

async fn sync_provider(db: &PgPool, domain: &str) -> Result<WellKnown> {
    let wk = fetch_well_known(domain).await?;

    state::providers::upsert(db, &wk.domain, &wk.name, &wk.base_url, wk.max_results).await?;

    for cap in &wk.capabilities {
        state::providers::upsert_capability(
            db,
            &wk.domain,
            &cap.resource,
            &cap.algorithm,
            &cap.description,
            &cap.filters,
        )
        .await?;
    }

    Ok(wk)
}

pub async fn register(
    db: &PgPool,
    domain: &str,
    instance_domain: &str,
    instance_name: &str,
) -> Result<()> {
    let wk = sync_provider(db, domain).await?;

    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/register", wk.base_url))
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

    state::providers::save_registration(
        db,
        &wk.domain,
        &resp.api_key,
        &resp.request_id,
        &resp.status,
        &resp.verify_path,
    )
    .await?;

    println!("Registration submitted!");
    println!("  Status:      {}", resp.status);
    println!("  Verify path: {}", resp.verify_path);
    println!("\nThe provider will verify your domain. Check status with:");
    println!("  fediway-cli provider status {domain}");

    Ok(())
}

pub async fn status(db: &PgPool, domain: &str) -> Result<()> {
    let wk = sync_provider(db, domain).await?;

    let Some((api_key, current_status)) =
        state::providers::find_registration(db, &wk.domain).await?
    else {
        anyhow::bail!("Not registered yet. Run `provider register {domain}` first.");
    };

    if current_status.as_deref() == Some("approved") {
        println!("Already approved.");
        return Ok(());
    }

    let Some(api_key) = api_key else {
        anyhow::bail!("Not registered yet. Run `provider register {domain}` first.");
    };

    let client = reqwest::Client::new();
    let resp = client
        .get(format!("{}/register/status", wk.base_url))
        .bearer_auth(&api_key)
        .send()
        .await?
        .error_for_status()?
        .json::<StatusResponse>()
        .await?;

    state::providers::update_status(db, &wk.domain, &resp.status).await?;

    println!("Status: {}", resp.status);
    if let Some(msg) = &resp.message {
        println!("Message: {msg}");
    }

    Ok(())
}

#[derive(sqlx::FromRow)]
struct ProviderRow {
    domain: String,
    name: String,
    status: Option<String>,
    enabled: bool,
    api_key: Option<String>,
    base_url: String,
}

pub async fn list(db: &PgPool) -> Result<()> {
    let rows = sqlx::query_as::<_, ProviderRow>(
        "SELECT domain, name, status, enabled, api_key, base_url
         FROM commonfeed_providers
         ORDER BY domain",
    )
    .fetch_all(db)
    .await?;

    if rows.is_empty() {
        println!("no providers configured");
        return Ok(());
    }

    let header = format!(
        "{:<35} {:<25} {:<10} {:<8} {}",
        "DOMAIN", "NAME", "STATUS", "ENABLED", "API KEY"
    );
    println!("{header}");
    println!("{}", "-".repeat(110));

    for r in &rows {
        let status = r.status.as_deref().unwrap_or("—");
        let enabled = if r.enabled { "yes" } else { "no" };
        let key = r.api_key.as_deref().unwrap_or("—");
        println!(
            "{:<35} {:<25} {:<10} {:<8} {}",
            r.domain, r.name, status, enabled, key
        );
    }

    println!("\n{} provider(s)", rows.len());
    Ok(())
}
