#[global_allocator]
static GLOBAL: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;

use axum::extract::DefaultBodyLimit;
use tokio::net::TcpListener;
use tower::ServiceBuilder;
use tracing_subscriber::EnvFilter;

pub mod auth;
pub mod language;
mod middleware;
mod observe;
mod routes;
pub mod state;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _ = dotenvy::dotenv();

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let config = config::FediwayConfig::load();
    config::metrics::init(config.instance.metrics_port);

    let pool = ::state::db::connect(&config.db)
        .await
        .expect("failed to connect to database");

    let app_state = crate::state::AppStateInner::new(pool);

    let app = routes::router(app_state, &config.instance.instance_domain).layer(
        ServiceBuilder::new()
            .layer(middleware::MetricsLayer)
            .layer(DefaultBodyLimit::max(1_048_576)),
    );

    let addr = format!(
        "{}:{}",
        config.instance.server_host, config.instance.server_port
    );
    tracing::info!("listening on {addr}");
    let listener = TcpListener::bind(&addr).await.expect("failed to bind");
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    tracing::info!("shut down");
    Ok(())
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c().await.ok();
    tracing::info!("received shutdown signal");
}
