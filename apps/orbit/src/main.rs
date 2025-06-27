mod algo;
mod config;
mod embeddings;
mod models;
mod rw;
mod services;
mod sparse;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "orbit=trace".into()),
        )
        .init();

    tracing::info!("Starting orbit.");

    let config = config::Config::from_env();

    tracing::info!("Loaded config.");

    let _embeddings =
        services::compute_initial_embeddings::compute_initial_embeddings(&config).await;

    tracing::info!("Done.");
}
