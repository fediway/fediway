mod communities;
mod config;
mod db;
mod debezium;
mod embedding;
mod entities;
mod init;
mod orbit;
mod rw;
mod sparse;
mod types;
mod utils;
mod workers;

use std::io;
use std::io::prelude::*;

use crate::init::compute_embeddings;

fn parse_comunities() -> communities::Communities {
    tracing::info!("Parsing communities from stdin...");

    let stdin = io::stdin();
    let mut communies: Vec<Vec<i64>> = Vec::default();

    for line in stdin.lock().lines() {
        let community: Vec<i64> = line
            .expect("Failed to read communities from stdin")
            .split(',')
            .map(|s| s.parse::<i64>().expect("Failed to parse tag id"))
            .collect();

        communies.push(community);
    }

    communities::Communities::from(communies)
}

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

    let communities = parse_comunities();

    let embeddings = compute_embeddings(config, communities).await;

    // let orbit = orbit::Orbit::new(config.clone(), init::get_initial_embeddings(config).await);

    // orbit.start().await;
}
