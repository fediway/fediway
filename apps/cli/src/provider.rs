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

pub async fn enable(db: &PgPool, domain: &str, capability: &str) -> Result<()> {
    let wk = sync_provider(db, domain).await?;
    let (resource, algorithm) = parse_capability(capability)?;
    let rows =
        state::providers::set_capability_enabled(db, &wk.domain, resource, algorithm, true).await?;

    if rows == 0 {
        anyhow::bail!(
            "Capability '{capability}' not found for provider '{}'.",
            wk.domain
        );
    }

    println!("Enabled {capability} for {}.", wk.domain);
    Ok(())
}

pub async fn disable(db: &PgPool, domain: &str, capability: &str) -> Result<()> {
    let wk = sync_provider(db, domain).await?;
    let (resource, algorithm) = parse_capability(capability)?;
    let rows = state::providers::set_capability_enabled(db, &wk.domain, resource, algorithm, false)
        .await?;

    if rows == 0 {
        anyhow::bail!(
            "Capability '{capability}' not found for provider '{}'.",
            wk.domain
        );
    }

    println!("Disabled {capability} for {}.", wk.domain);
    Ok(())
}

fn parse_capability(capability: &str) -> Result<(&str, &str)> {
    capability.split_once('/').ok_or_else(|| {
        anyhow::anyhow!("Capability must be in format 'resource/algorithm' (e.g. posts/trending)")
    })
}
