use anyhow::Result;
use clap::{Parser, Subcommand};

mod provider;

#[derive(Parser)]
#[command(name = "fediway-cli")]
struct Cli {
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
}

#[derive(Subcommand)]
enum ProviderCommand {
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
    /// Enable a capability (e.g. trending, search)
    Enable { domain: String, capability: String },
    /// Disable a capability
    Disable { domain: String, capability: String },
}

#[tokio::main]
async fn main() -> Result<()> {
    let _ = dotenvy::dotenv();
    let cli = Cli::parse();

    match cli.command {
        Command::Migrate => {
            let config = config::FediwayConfig::load();
            let db = state::db::connect(&config.db).await?;
            state::db::migrate(&db).await?;
            println!("migrations complete");
            return Ok(());
        }
        Command::Provider { command } => match command {
            ProviderCommand::Info { domain } => {
                provider::info(&domain).await?;
            }
            cmd => {
                let config = config::FediwayConfig::load();
                let db = state::db::connect(&config.db).await?;
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
                    ProviderCommand::Enable { domain, capability } => {
                        provider::enable(&db, &domain, &capability).await?;
                    }
                    ProviderCommand::Disable { domain, capability } => {
                        provider::disable(&db, &domain, &capability).await?;
                    }
                    ProviderCommand::Info { .. } => unreachable!(),
                }
            }
        },
    }

    Ok(())
}
