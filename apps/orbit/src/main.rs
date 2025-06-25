
use std::time::{SystemTime};
use std::collections::HashMap;

mod algo;
mod services;
mod config;
mod models;
mod rw;
mod state;
mod utils;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| {
            "orbit=trace".into()
        }),)
        .init();

    tracing::info!("Starting orbit.");

    let config = config::Config::from_env();
    let mut state = state::State::new();

    tracing::info!("Loaded config.");

    let (db, connection) = tokio_postgres::connect(&config.rw_conn(), tokio_postgres::NoTls)
        .await
        .unwrap();

    tracing::info!("Connected to risingwave.");

    tokio::spawn(async move {
        if let Err(e) = connection.await {
            tracing::error!("connection error: {}", e);
        }
    });

    // 1. compute communities
    let communities = services::compute_communities::compute_communities(&config, &db).await;

    // 2. compute consumer embeddings
    let e_u = 

    // 3. compute producer embeddings

    // 4. compute tag embeddings

    // 5. stream initial statuses and events

    // 6. run

    tracing::info!("Done.");
}
