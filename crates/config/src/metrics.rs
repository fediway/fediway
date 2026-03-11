use std::time::Duration;

use metrics_exporter_prometheus::PrometheusBuilder;

/// Initialize the Prometheus metrics exporter.
///
/// If `port` is `Some`, starts an HTTP server on `0.0.0.0:{port}` serving
/// `GET /metrics`. Also installs process metrics (CPU, memory, FDs, etc.)
/// that update every 5 seconds.
///
/// If `port` is `None`, does nothing — all `metrics::*!()` calls become
/// zero-cost no-ops since no recorder is installed.
#[allow(clippy::unreadable_literal)]
pub fn init(port: Option<u16>) {
    let Some(port) = port else { return };

    let builder = PrometheusBuilder::new()
        .with_http_listener(([0, 0, 0, 0], port))
        // HTTP request duration: fast API responses, 1ms to 10s.
        .set_buckets_for_metric(
            metrics_exporter_prometheus::Matcher::Suffix("request_duration_seconds".to_string()),
            &[
                0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
            ],
        )
        .unwrap()
        // Source fetch duration: 10ms to 30s (external HTTP to provider).
        .set_buckets_for_metric(
            metrics_exporter_prometheus::Matcher::Suffix("fetch_duration_seconds".to_string()),
            &[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
        .unwrap()
        // Feed duration: 10ms to 30s (source fetch + scoring + sampling).
        .set_buckets_for_metric(
            metrics_exporter_prometheus::Matcher::Suffix("feed_duration_seconds".to_string()),
            &[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
        .unwrap()
        // Per-source fetch duration inside the feed.
        .set_buckets_for_metric(
            metrics_exporter_prometheus::Matcher::Suffix(
                "feed_source_duration_seconds".to_string(),
            ),
            &[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
        .unwrap()
        // Scorer duration: sub-millisecond to 1s (CPU-bound).
        .set_buckets_for_metric(
            metrics_exporter_prometheus::Matcher::Suffix(
                "feed_scorer_duration_seconds".to_string(),
            ),
            &[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
        )
        .unwrap()
        // Candidate funnel counts: 0 to 500 items.
        .set_buckets_for_metric(
            metrics_exporter_prometheus::Matcher::Suffix("feed_collected".to_string()),
            &[0.0, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0],
        )
        .unwrap()
        .set_buckets_for_metric(
            metrics_exporter_prometheus::Matcher::Suffix("feed_filtered".to_string()),
            &[0.0, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0],
        )
        .unwrap()
        .set_buckets_for_metric(
            metrics_exporter_prometheus::Matcher::Suffix("feed_returned".to_string()),
            &[0.0, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0],
        )
        .unwrap()
        .set_buckets_for_metric(
            metrics_exporter_prometheus::Matcher::Suffix("feed_source_candidates".to_string()),
            &[0.0, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0],
        )
        .unwrap();

    match builder.install() {
        Ok(()) => {
            tracing::info!(port, "metrics server started on :{port}");

            let collector = metrics_process::Collector::default();
            collector.describe();

            tokio::spawn(async move {
                let mut interval = tokio::time::interval(Duration::from_secs(5));
                loop {
                    interval.tick().await;
                    collector.collect();
                }
            });
        }
        Err(e) => {
            tracing::warn!("failed to start metrics server: {e}");
        }
    }
}
