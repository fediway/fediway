use std::time::Duration;

use clap::Parser;
use sqlx::PgPool;
use tokio::time;
use tracing_subscriber::EnvFilter;

mod embed;
mod engagement;
mod poll;
mod tei;
mod vector;

use embed::EmbeddingTemplate;
use engagement::{EngagementKind, RawEngagement};
use tei::TeiClient;

#[derive(Parser)]
#[command(name = "fediway-orbit")]
struct Args {
    #[command(flatten)]
    db: config::DatabaseConfig,

    #[command(flatten)]
    tei: config::TeiConfig,

    #[command(flatten)]
    orbit: config::OrbitConfig,

    /// Instance domain for author handle resolution (e.g. social.example)
    #[arg(long, env = "INSTANCE_DOMAIN")]
    instance_domain: String,

    /// Prometheus metrics port (optional)
    #[arg(long, env = "METRICS_PORT")]
    metrics_port: Option<u16>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _ = dotenvy::dotenv();

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let args = Args::parse();

    config::metrics::init(args.metrics_port);

    let pool = state::db::connect(&args.db)
        .await
        .expect("failed to connect to database");
    state::db::check(&pool)
        .await
        .expect("database check failed");
    tracing::info!("postgres ready");

    init_cursors(&pool, args.orbit.orbit_replay_hours).await;

    let tei_client = TeiClient::new(&args.tei);
    let template = EmbeddingTemplate::new();

    let poll_interval = Duration::from_secs(args.orbit.orbit_poll_interval_secs);

    tracing::info!(
        poll_interval_secs = args.orbit.orbit_poll_interval_secs,
        alpha = args.orbit.orbit_alpha,
        dims = args.orbit.orbit_dims,
        model = %args.orbit.orbit_model_name,
        tei_url = %args.tei.tei_url,
        instance_domain = %args.instance_domain,
        "orbit worker starting"
    );

    let mut interval = time::interval(poll_interval);
    interval.set_missed_tick_behavior(time::MissedTickBehavior::Delay);

    loop {
        tokio::select! {
            _ = interval.tick() => {
                poll_cycle(&pool, &args, &tei_client, &template).await;
            }
            () = shutdown_signal() => {
                tracing::info!("shutting down");
                break;
            }
        }
    }

    Ok(())
}

async fn init_cursors(pool: &PgPool, replay_hours: u64) {
    let kinds = [
        EngagementKind::Like,
        EngagementKind::Repost,
        EngagementKind::Reply,
    ];

    for kind in kinds {
        let cursor = poll::load_cursor(pool, kind.as_str()).await;
        if cursor == 0 {
            let start = poll::init_cursor(pool, kind, replay_hours).await;
            if start > 0 {
                poll::save_cursor(pool, kind.as_str(), start).await;
                tracing::info!(source = kind.as_str(), cursor = start, "initialized cursor");
            }
        }
    }
}

async fn poll_cycle(
    pool: &PgPool,
    args: &Args,
    tei_client: &TeiClient,
    template: &EmbeddingTemplate,
) {
    let start = std::time::Instant::now();

    let batch_size = args.orbit.orbit_batch_size;
    let domain = &args.instance_domain;

    let (likes_cursor, reposts_cursor, replies_cursor) = tokio::join!(
        poll::load_cursor(pool, EngagementKind::Like.as_str()),
        poll::load_cursor(pool, EngagementKind::Repost.as_str()),
        poll::load_cursor(pool, EngagementKind::Reply.as_str()),
    );

    let (likes, reposts, replies) = tokio::join!(
        poll::poll_favourites(pool, likes_cursor, batch_size, domain),
        poll::poll_reblogs(pool, reposts_cursor, batch_size, domain),
        poll::poll_replies(pool, replies_cursor, batch_size, domain),
    );

    let sources = [
        (EngagementKind::Like, likes),
        (EngagementKind::Repost, reposts),
        (EngagementKind::Reply, replies),
    ];

    let mut engagements: Vec<RawEngagement> = Vec::new();

    for (kind, result) in sources {
        match result {
            Ok(batch) => engagements.extend(batch),
            Err(e) => {
                tracing::warn!(source = kind.as_str(), error = %e, "poll failed");
            }
        }
    }

    if engagements.is_empty() {
        return;
    }

    engagements.sort_by_key(|e| e.created_at);

    let likes_count = engagements
        .iter()
        .filter(|e| e.kind == EngagementKind::Like)
        .count();
    let reposts_count = engagements
        .iter()
        .filter(|e| e.kind == EngagementKind::Repost)
        .count();
    let replies_count = engagements
        .iter()
        .filter(|e| e.kind == EngagementKind::Reply)
        .count();

    tracing::info!(
        likes = likes_count,
        reposts = reposts_count,
        replies = replies_count,
        total = engagements.len(),
        elapsed_ms = start.elapsed().as_millis() as u64,
        "polled engagements"
    );

    let embeddings = embed::embed_engagements(
        tei_client,
        template,
        &engagements,
        args.orbit.orbit_dims,
        args.tei.tei_batch_size,
    )
    .await;

    if embeddings.is_empty() {
        tracing::warn!("no embeddings produced, skipping cycle (cursors unchanged)");
        return;
    }

    tracing::info!(unique_texts = embeddings.len(), "computed embeddings");

    vector::process_engagements(
        pool,
        &engagements,
        &embeddings,
        template,
        args.orbit.orbit_alpha as f32,
        args.orbit.orbit_dims,
    )
    .await;

    // Advance cursors only to the last engagement per source that had a
    // successful embedding. Engagements whose TEI batch failed remain ahead
    // of the cursor and will be retried next cycle.
    for kind in [
        EngagementKind::Like,
        EngagementKind::Repost,
        EngagementKind::Reply,
    ] {
        let max_processed = engagements
            .iter()
            .filter(|e| e.kind == kind)
            .filter(|e| {
                let rendered = template.render(&e.target);
                embeddings.contains_key(&rendered)
            })
            .map(|e| e.id)
            .max();

        if let Some(id) = max_processed {
            poll::save_cursor(pool, kind.as_str(), id).await;
        }
    }
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c().await.ok();
    tracing::info!("received shutdown signal");
}
