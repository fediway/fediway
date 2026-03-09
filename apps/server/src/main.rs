use tokio::net::TcpListener;
use tracing_subscriber::EnvFilter;

pub mod auth;
pub mod language;
mod routes;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _ = dotenvy::dotenv();

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let config = config::FediwayConfig::load();
    let db = state::db::connect(&config.db)
        .await
        .expect("failed to connect to database");

    let app = routes::router(db, &config.instance.instance_domain);

    let addr = format!(
        "{}:{}",
        config.instance.server_host, config.instance.server_port
    );
    tracing::info!("listening on {addr}");
    let listener = TcpListener::bind(&addr).await.expect("failed to bind");
    axum::serve(listener, app).await?;

    Ok(())
}
