use std::time::Duration;

/// Record a provider fetch attempt with outcome and duration.
pub fn source_fetched(provider: &str, result: &str, duration: Duration) {
    metrics::counter!(
        "fediway_source_fetch_total",
        "provider" => provider.to_string(),
        "result" => result.to_string()
    )
    .increment(1);

    metrics::histogram!(
        "fediway_source_fetch_duration_seconds",
        "provider" => provider.to_string()
    )
    .record(duration.as_secs_f64());
}
