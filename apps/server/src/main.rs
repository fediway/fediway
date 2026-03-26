#[global_allocator]
static GLOBAL: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;

use axum::extract::DefaultBodyLimit;
use clap::Parser;
use tokio::net::TcpListener;
use tower::ServiceBuilder;
use tracing_subscriber::EnvFilter;

pub mod auth;
pub mod language;
mod middleware;
mod observe;
mod routes;
pub mod state;

#[derive(Parser)]
#[command(name = "fediway-server")]
struct Args {
    #[command(flatten)]
    db: config::DatabaseConfig,

    #[command(flatten)]
    redis: config::RedisConfig,

    #[command(flatten)]
    instance: config::InstanceConfig,

    /// Embedding model name for Orbit recommended requests
    #[arg(long, env = "ORBIT_MODEL_NAME", default_value = "qwen3_256d")]
    orbit_model_name: String,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _ = dotenvy::dotenv();

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let args = Args::parse();
    config::metrics::init(args.instance.metrics_port);

    let pool = ::state::db::connect(&args.db)
        .await
        .expect("failed to connect to database");
    ::state::db::check(&pool)
        .await
        .expect("database check failed");
    tracing::info!("postgres ready");

    let app_state = crate::state::AppStateInner::new(pool, args.orbit_model_name);

    let app = routes::router(app_state, &args.instance.instance_domain).layer(
        ServiceBuilder::new()
            .layer(middleware::MetricsLayer)
            .layer(DefaultBodyLimit::max(1_048_576)),
    );

    let addr = format!(
        "{}:{}",
        args.instance.server_host, args.instance.server_port
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
