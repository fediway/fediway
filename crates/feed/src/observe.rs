use std::time::Duration;

/// Record candidates collected from a single source within a feed.
#[allow(clippy::cast_precision_loss)]
pub fn source_collected(feed: &str, source: &str, candidates: usize, duration: Duration) {
    metrics::histogram!(
        "fediway_feed_source_candidates",
        "feed" => feed.to_string(),
        "source" => source.to_string()
    )
    .record(candidates as f64);

    metrics::histogram!(
        "fediway_feed_source_duration_seconds",
        "feed" => feed.to_string(),
        "source" => source.to_string()
    )
    .record(duration.as_secs_f64());
}

/// Record a single scorer pass duration with scorer identity.
pub fn scorer_applied(feed: &str, scorer: &str, duration: Duration) {
    metrics::histogram!(
        "fediway_feed_scorer_duration_seconds",
        "feed" => feed.to_string(),
        "scorer" => scorer.to_string()
    )
    .record(duration.as_secs_f64());
}

/// Record the full feed execution funnel: collected → filtered → returned.
#[allow(clippy::cast_precision_loss)]
pub fn executed(
    feed: &str,
    collected: usize,
    filtered: usize,
    returned: usize,
    duration: Duration,
) {
    let feed = feed.to_string();

    metrics::histogram!("fediway_feed_collected", "feed" => feed.clone()).record(collected as f64);
    metrics::histogram!("fediway_feed_filtered", "feed" => feed.clone()).record(filtered as f64);
    metrics::histogram!("fediway_feed_returned", "feed" => feed.clone()).record(returned as f64);
    metrics::histogram!("fediway_feed_duration_seconds", "feed" => feed)
        .record(duration.as_secs_f64());
}
