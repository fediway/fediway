/// Record which languages were requested for content filtering.
pub fn language_requested(languages: &[String]) {
    for lang in languages {
        metrics::counter!(
            "fediway_language_requested_total",
            "language" => lang.clone()
        )
        .increment(1);
    }
}
