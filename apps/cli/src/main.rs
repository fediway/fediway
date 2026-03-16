use anyhow::Result;
use clap::{Parser, Subcommand};

mod provider;

#[derive(Parser)]
#[command(name = "fediway-cli")]
struct Cli {
    #[command(flatten)]
    db: config::DatabaseConfig,

    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Run database migrations
    Migrate,
    /// Manage content providers
    Provider {
        #[command(subcommand)]
        command: ProviderCommand,
    },
    /// Enable a provider source for a route (e.g. enable trends/statuses localhost:3000 posts/trending)
    Enable {
        /// Fediway route (e.g. trends/statuses, timelines/tag, trends/tags)
        route: String,
        /// Provider domain
        provider: String,
        /// Capability to use (e.g. posts/trending, posts/hot, tags/trending)
        capability: String,
    },
    /// Disable a provider source for a route
    Disable {
        /// Fediway route
        route: String,
        /// Provider domain
        provider: String,
    },
}

#[derive(Subcommand)]
enum ProviderCommand {
    /// List all providers with status and API key
    List,
    /// Show provider info (no DB, just fetches well-known)
    Info { domain: String },
    /// Add a provider to the database
    Add { domain: String },
    /// Register this instance with a provider
    Register {
        domain: String,
        #[arg(long, env = "INSTANCE_DOMAIN")]
        instance_domain: String,
        #[arg(long, env = "INSTANCE_NAME")]
        instance_name: String,
    },
    /// Check registration status
    Status { domain: String },
}

fn parse_capability(capability: &str) -> Result<(&str, &str)> {
    capability.split_once('/').ok_or_else(|| {
        anyhow::anyhow!("Capability must be in format 'resource/algorithm' (e.g. posts/trending)")
    })
}

#[tokio::main]
async fn main() -> Result<()> {
    let _ = dotenvy::dotenv();
    let cli = Cli::parse();

    match cli.command {
        Command::Migrate => {
            let db = state::db::connect(&cli.db).await?;
            state::db::check(&db).await?;
            state::db::migrate(&db).await?;
            println!("migrations complete");
        }
        Command::Provider { command } => match command {
            ProviderCommand::Info { domain } => {
                provider::info(&domain).await?;
            }
            ProviderCommand::List => {
                let db = state::db::connect(&cli.db).await?;
                state::db::check(&db).await?;
                provider::list(&db).await?;
            }
            cmd => {
                let db = state::db::connect(&cli.db).await?;
                state::db::check(&db).await?;
                match cmd {
                    ProviderCommand::Add { domain } => {
                        provider::add(&db, &domain).await?;
                    }
                    ProviderCommand::Register {
                        domain,
                        instance_domain,
                        instance_name,
                    } => {
                        provider::register(&db, &domain, &instance_domain, &instance_name).await?;
                    }
                    ProviderCommand::Status { domain } => {
                        provider::status(&db, &domain).await?;
                    }
                    ProviderCommand::Info { .. } | ProviderCommand::List => unreachable!(),
                }
            }
        },
        Command::Enable {
            route,
            provider,
            capability,
        } => {
            let (resource, algorithm) = parse_capability(&capability)?;
            let db = state::db::connect(&cli.db).await?;
            state::db::check(&db).await?;
            let domain = provider::resolve_domain(&db, &provider).await?;
            state::providers::enable_source(&db, &route, &domain, resource, algorithm).await?;
            println!("Enabled {route} ← {domain} ({capability})");
        }
        Command::Disable { route, provider } => {
            let db = state::db::connect(&cli.db).await?;
            state::db::check(&db).await?;
            let domain = provider::resolve_domain(&db, &provider).await?;
            let rows = state::providers::disable_source(&db, &route, &domain).await?;
            if rows == 0 {
                anyhow::bail!("No source found for {route} from {domain}");
            }
            println!("Disabled {route} ← {domain}");
        }
    }

    Ok(())
}
