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

    /// Wipe `orbit_cursors` and `orbit_user_vectors` before starting. Use
    /// after fixing data issues or changing the embedding model — pair
    /// with `ORBIT_REPLAY_HOURS=0` to replay full history from scratch.
    #[arg(long, env = "ORBIT_FRESH", default_value_t = false)]
    fresh: bool,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _ = dotenvy::dotenv();

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let args = Args::parse();
    anyhow::ensure!(args.orbit.orbit_dims > 0, "orbit_dims must be > 0");
    anyhow::ensure!(args.orbit.orbit_alpha > 0.0, "orbit_alpha must be > 0");
    anyhow::ensure!(
        args.orbit.orbit_poll_interval_secs > 0,
        "orbit_poll_interval_secs must be > 0"
    );
    anyhow::ensure!(
        args.orbit.orbit_batch_size > 0,
        "orbit_batch_size must be > 0"
    );

    config::metrics::init(args.metrics_port);
    metrics::gauge!("build_info", "service" => "fediway-orbit", "version" => env!("CARGO_PKG_VERSION")).set(1.0);

    let pool = state::db::connect(&args.db)
        .await
        .expect("failed to connect to database");
    state::db::check(&pool)
        .await
        .expect("database check failed");
    tracing::info!("postgres ready");

    if args.fresh {
        tracing::warn!("--fresh set: wiping orbit_cursors and orbit_user_vectors before startup");
        let cursors = state::orbit::wipe_cursors(&pool)
            .await
            .expect("failed to wipe orbit_cursors");
        let vectors = state::orbit::wipe_vectors(&pool)
            .await
            .expect("failed to wipe orbit_user_vectors");
        tracing::info!(
            cursors_deleted = cursors,
            vectors_deleted = vectors,
            "orbit state wiped"
        );
    }

    init_cursors(&pool, args.orbit.orbit_replay_hours).await?;

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

async fn init_cursors(pool: &PgPool, replay_hours: u64) -> anyhow::Result<()> {
    let kinds = [
        EngagementKind::Like,
        EngagementKind::Repost,
        EngagementKind::Reply,
        EngagementKind::Bookmark,
    ];

    for kind in kinds {
        if poll::load_cursor(pool, kind.as_str()).await?.is_none() {
            let start = poll::init_cursor(pool, kind, replay_hours).await?;
            if start > 0 {
                poll::save_cursor(pool, kind.as_str(), start).await;
                tracing::info!(source = kind.as_str(), cursor = start, "initialized cursor");
            }
        }
    }

    Ok(())
}

#[allow(clippy::too_many_lines, clippy::cast_precision_loss)]
async fn poll_cycle(
    pool: &PgPool,
    args: &Args,
    tei_client: &TeiClient,
    template: &EmbeddingTemplate,
) {
    let cycle_start = std::time::Instant::now();
    metrics::counter!("fediway_orbit_cycle_total").increment(1);

    let batch_size = args.orbit.orbit_batch_size;
    let domain = &args.instance_domain;

    let cursors = tokio::try_join!(
        poll::load_cursor(pool, EngagementKind::Like.as_str()),
        poll::load_cursor(pool, EngagementKind::Repost.as_str()),
        poll::load_cursor(pool, EngagementKind::Reply.as_str()),
        poll::load_cursor(pool, EngagementKind::Bookmark.as_str()),
    );
    let (likes_cursor, reposts_cursor, replies_cursor, bookmarks_cursor) = match cursors {
        Ok((l, r, rp, b)) => (
            l.unwrap_or(0),
            r.unwrap_or(0),
            rp.unwrap_or(0),
            b.unwrap_or(0),
        ),
        Err(e) => {
            metrics::counter!("fediway_orbit_cursor_load_errors_total").increment(1);
            tracing::warn!(error = %e, "failed to load cursors, skipping cycle");
            return;
        }
    };

    let poll_start = std::time::Instant::now();
    let (likes, reposts, replies, bookmarks) = tokio::join!(
        poll::poll_favourites(pool, likes_cursor, batch_size, domain),
        poll::poll_reblogs(pool, reposts_cursor, batch_size, domain),
        poll::poll_replies(pool, replies_cursor, batch_size, domain),
        poll::poll_bookmarks(pool, bookmarks_cursor, batch_size, domain),
    );
    let poll_elapsed = poll_start.elapsed().as_secs_f64();
    metrics::histogram!("fediway_orbit_poll_duration_seconds").record(poll_elapsed);

    let sources = [
        (EngagementKind::Like, likes),
        (EngagementKind::Repost, reposts),
        (EngagementKind::Reply, replies),
        (EngagementKind::Bookmark, bookmarks),
    ];

    let mut engagements: Vec<RawEngagement> = Vec::new();

    for (kind, result) in sources {
        let source = kind.as_str();
        match result {
            Ok(batch) => {
                let count = batch.len() as u64;
                metrics::counter!("fediway_orbit_poll_total", "source" => source).increment(count);
                metrics::histogram!("fediway_orbit_poll_results", "source" => source)
                    .record(count as f64);
                engagements.extend(batch);
            }
            Err(e) => {
                metrics::counter!("fediway_orbit_poll_errors_total", "source" => source)
                    .increment(1);
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
        elapsed_ms = cycle_start.elapsed().as_millis() as u64,
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

    metrics::counter!("fediway_orbit_texts_embedded_total").increment(embeddings.len() as u64);
    tracing::info!(unique_texts = embeddings.len(), "computed embeddings");

    if let Err(e) = vector::process_engagements(
        pool,
        &engagements,
        &embeddings,
        template,
        args.orbit.orbit_alpha as f32,
        args.orbit.orbit_dims,
    )
    .await
    {
        metrics::counter!("fediway_orbit_vector_process_errors_total").increment(1);
        tracing::warn!(error = %e, "failed to process engagements, skipping cursor advance");
        return;
    }

    // Advance cursors only to the last engagement per source that had a
    // successful embedding. Engagements whose TEI batch failed remain ahead
    // of the cursor and will be retried next cycle.
    for kind in [
        EngagementKind::Like,
        EngagementKind::Repost,
        EngagementKind::Reply,
        EngagementKind::Bookmark,
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
            metrics::gauge!("fediway_orbit_cursor_position", "source" => kind.as_str())
                .set(id as f64);
        }
    }

    metrics::histogram!("fediway_orbit_cycle_duration_seconds")
        .record(cycle_start.elapsed().as_secs_f64());
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c().await.ok();
    tracing::info!("received shutdown signal");
}
