mod communities;
mod config;
mod embedding;
mod init;
mod kafka;
mod orbit;
mod qdrant;
mod rw;
mod sparse;
mod types;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "orbit=trace".into()),
        )
        .init();

    tracing::info!("Starting orbit...");

    let config = config::Config::from_env();

    let orbit = orbit::Orbit::new(config.clone(), init::get_initial_embeddings(config).await);

    orbit.start().await;
}
