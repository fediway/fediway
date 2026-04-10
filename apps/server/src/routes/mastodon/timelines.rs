use axum::Json;
use axum::extract::{Path, Query, State};
use axum::http::{HeaderMap, HeaderValue, StatusCode, header};
use axum::response::IntoResponse;
use common::types::Post;
use feed::feed::Feed;
use feed::filter::Dedup;
use feed::scorer::Diversity;
use mastodon::Status;
use serde::Deserialize;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::recommended::RecommendedSource;
use sources::commonfeed::types::QueryFilters;

use crate::auth::Account;
use crate::language::resolve_languages;
use crate::observe;
use crate::state::AppState;

/// Mastodon-compatible keyset pagination for timeline endpoints.
#[derive(Deserialize)]
pub struct TimelineParams {
    #[serde(default = "default_limit")]
    limit: usize,
    max_id: Option<String>,
    min_id: Option<String>,
    since_id: Option<String>,
}

#[derive(Deserialize)]
pub struct TagParams {
    #[serde(default = "default_limit")]
    limit: usize,
    max_id: Option<String>,
    min_id: Option<String>,
    since_id: Option<String>,
    // hashtag comes from path, not query
}

#[derive(Deserialize)]
pub struct LinkParams {
    url: String,
    #[serde(default = "default_limit")]
    limit: usize,
    max_id: Option<String>,
    min_id: Option<String>,
    since_id: Option<String>,
}

const fn default_limit() -> usize {
    20
}

const POOL_SIZE: usize = 100;

/// Filter statuses by Mastodon keyset pagination bounds, return Link header.
fn paginate_statuses(
    mut statuses: Vec<Status>,
    limit: usize,
    max_id: Option<&str>,
    min_id: Option<&str>,
    since_id: Option<&str>,
    domain: &str,
    path: &str,
) -> (Vec<Status>, HeaderMap) {
    // Filter by ID bounds (IDs are numeric snowflakes, compared as strings
    // which works because snowflakes are fixed-width and zero-padded... actually
    // they're not zero-padded. Compare as i64.)
    if let Some(max) = max_id.and_then(|s| s.parse::<i64>().ok()) {
        statuses.retain(|s| s.id.parse::<i64>().is_ok_and(|id| id < max));
    }
    if let Some(min) = min_id.and_then(|s| s.parse::<i64>().ok()) {
        statuses.retain(|s| s.id.parse::<i64>().is_ok_and(|id| id > min));
    }
    if let Some(since) = since_id.and_then(|s| s.parse::<i64>().ok()) {
        statuses.retain(|s| s.id.parse::<i64>().is_ok_and(|id| id > since));
    }

    statuses.truncate(limit);

    let mut headers = HeaderMap::new();
    if let (Some(last), Some(first)) = (statuses.last(), statuses.first()) {
        let next = format!("<https://{domain}{path}?max_id={}>; rel=\"next\"", last.id);
        let prev = format!("<https://{domain}{path}?min_id={}>; rel=\"prev\"", first.id);
        if let Ok(value) = HeaderValue::from_str(&format!("{next}, {prev}")) {
            headers.insert(header::LINK, value);
        }
    }

    (statuses, headers)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn status_with_id(id: &str) -> Status {
        let post = common::types::Post {
            provider_id: None,
            provider_domain: None,
            url: format!("https://example.com/{id}"),
            uri: None,
            content: String::new(),
            text: String::new(),
            author: common::types::Author {
                handle: "test".into(),
                display_name: "Test".into(),
                url: "https://example.com/@test".into(),
                avatar_url: None,
                emojis: vec![],
            },
            published_at: chrono::Utc::now(),
            language: None,
            sensitive: false,
            content_warning: None,
            media: vec![],
            engagement: common::types::Engagement {
                replies: 0,
                reposts: 0,
                likes: 0,
            },
            link: None,
            reply_to: None,
            quote: None,
            tags: vec![],
            emojis: vec![],
        };
        Status::from_post(post, id.to_string())
    }

    fn ids(statuses: &[Status]) -> Vec<&str> {
        statuses.iter().map(|s| s.id.as_str()).collect()
    }

    #[test]
    fn paginate_first_page() {
        let statuses = vec![
            status_with_id("50"),
            status_with_id("40"),
            status_with_id("30"),
            status_with_id("20"),
            status_with_id("10"),
        ];

        let (page, headers) =
            paginate_statuses(statuses, 3, None, None, None, "example.com", "/api/v1/test");

        assert_eq!(ids(&page), vec!["50", "40", "30"]);
        let link = headers.get(header::LINK).unwrap().to_str().unwrap();
        assert!(link.contains("max_id=30"));
        assert!(link.contains("min_id=50"));
    }

    #[test]
    fn paginate_with_max_id() {
        let statuses = vec![
            status_with_id("50"),
            status_with_id("40"),
            status_with_id("30"),
            status_with_id("20"),
            status_with_id("10"),
        ];

        let (page, _) =
            paginate_statuses(statuses, 3, Some("40"), None, None, "example.com", "/test");

        assert_eq!(ids(&page), vec!["30", "20", "10"]);
    }

    #[test]
    fn paginate_with_min_id() {
        let statuses = vec![
            status_with_id("50"),
            status_with_id("40"),
            status_with_id("30"),
            status_with_id("20"),
            status_with_id("10"),
        ];

        let (page, _) =
            paginate_statuses(statuses, 3, None, Some("20"), None, "example.com", "/test");

        assert_eq!(ids(&page), vec!["50", "40", "30"]);
    }

    #[test]
    fn paginate_with_since_id() {
        let statuses = vec![
            status_with_id("50"),
            status_with_id("40"),
            status_with_id("30"),
            status_with_id("20"),
            status_with_id("10"),
        ];

        let (page, _) =
            paginate_statuses(statuses, 2, None, None, Some("30"), "example.com", "/test");

        assert_eq!(ids(&page), vec!["50", "40"]);
    }

    #[test]
    fn paginate_empty_result() {
        let (page, headers) =
            paginate_statuses(vec![], 20, None, None, None, "example.com", "/test");

        assert!(page.is_empty());
        assert!(headers.get(header::LINK).is_none());
    }

    #[test]
    fn paginate_max_id_excludes_all() {
        let statuses = vec![status_with_id("50"), status_with_id("40")];

        let (page, _) =
            paginate_statuses(statuses, 20, Some("10"), None, None, "example.com", "/test");

        assert!(page.is_empty());
    }

    #[test]
    fn paginate_non_numeric_ids_ignored() {
        let statuses = vec![
            status_with_id("https://example.com/1"),
            status_with_id("50"),
            status_with_id("40"),
        ];

        let (page, _) =
            paginate_statuses(statuses, 3, Some("45"), None, None, "example.com", "/test");

        // Non-numeric ID filtered out by parse check, numeric ones filtered by max_id
        assert_eq!(ids(&page), vec!["40"]);
    }
}

pub async fn home(
    account: Account,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<TimelineParams>,
) -> Result<impl IntoResponse, StatusCode> {
    let handler_start = std::time::Instant::now();
    metrics::counter!("fediway_home_requests_total").increment(1);

    let limit = params.limit.min(40);
    let languages = resolve_languages(&Some(account.clone()), &headers);

    let filters = QueryFilters {
        language: languages,
        ..Default::default()
    };

    let vector_start = std::time::Instant::now();
    let user_vector = state::orbit::load_vector(&state.pool, account.id).await;
    metrics::histogram!("fediway_home_vector_load_duration_seconds")
        .record(vector_start.elapsed().as_secs_f64());

    let (recommended_pool, trending_pool) = if let Some((_vector, count)) = &user_vector {
        metrics::counter!("fediway_home_vector_loaded_total", "result" => "found").increment(1);
        let confidence = (f64::from(i32::try_from(*count).unwrap_or(i32::MAX)) / 50.0).min(1.0);
        metrics::histogram!("fediway_home_confidence").record(confidence);
        (POOL_SIZE, 0)
    } else {
        metrics::counter!("fediway_home_vector_loaded_total", "result" => "cold_start")
            .increment(1);
        (0, 0)
    };

    #[allow(clippy::cast_precision_loss)]
    let recommended_pool_f64 = recommended_pool as f64;
    #[allow(clippy::cast_precision_loss)]
    let trending_pool_f64 = trending_pool as f64;
    metrics::histogram!("fediway_home_recommended_pool").record(recommended_pool_f64);
    metrics::histogram!("fediway_home_trending_pool").record(trending_pool_f64);

    let mut builder = Feed::builder().name("timelines/home");

    if let Some((vector, _count)) = &user_vector
        && recommended_pool > 0
    {
        let bound = state::providers::find_sources(&state.pool, "timelines/home").await;
        for b in bound {
            builder = builder.source(
                RecommendedSource::new(
                    b.provider,
                    b.algorithm,
                    vector.clone(),
                    &state.orbit_model_name,
                )
                .with_filters(filters.clone()),
                recommended_pool,
            );
        }
    }

    let trending = state::providers::find_sources(&state.pool, "trends/statuses").await;
    for b in trending {
        builder = builder.source(
            PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()),
            trending_pool,
        );
    }

    let feed = builder
        .filter(Dedup::new(|post: &Post| post.url.clone()))
        .score(Diversity::new(0.15, |post: &Post| {
            post.author.handle.clone()
        }))
        .build();

    let result = feed.execute(POOL_SIZE, &()).await;
    let posts: Vec<Post> = result.items.into_iter().map(|c| c.item).collect();
    let statuses = crate::commonfeed::posts_to_statuses(&state.pool, posts).await;

    let (statuses, response_headers) = paginate_statuses(
        statuses,
        limit,
        params.max_id.as_deref(),
        params.min_id.as_deref(),
        params.since_id.as_deref(),
        &state.instance_domain,
        "/api/v1/timelines/home",
    );

    #[allow(clippy::cast_precision_loss)]
    metrics::histogram!("fediway_home_results").record(statuses.len() as f64);

    metrics::histogram!("fediway_home_duration_seconds")
        .record(handler_start.elapsed().as_secs_f64());

    Ok((response_headers, Json(statuses)))
}

pub async fn tag(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(hashtag): Path<String>,
    Query(params): Query<TagParams>,
) -> Result<impl IntoResponse, StatusCode> {
    let limit = params.limit.min(40);
    let languages = resolve_languages(&account, &headers);
    observe::language_requested(&languages);

    let filters = QueryFilters {
        language: languages,
        tag: Some(hashtag.clone()),
        ..Default::default()
    };

    let bound = state::providers::find_sources(&state.pool, "timelines/tag").await;
    let sources = bound
        .into_iter()
        .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

    let feed = Feed::builder()
        .name("timelines/tag")
        .sources(sources, 100)
        .score(Diversity::new(0.1, |post: &Post| {
            post.author.handle.clone()
        }))
        .build();

    let result = feed.execute(POOL_SIZE, &()).await;
    let posts: Vec<Post> = result.items.into_iter().map(|c| c.item).collect();
    let statuses = crate::commonfeed::posts_to_statuses(&state.pool, posts).await;

    let (statuses, response_headers) = paginate_statuses(
        statuses,
        limit,
        params.max_id.as_deref(),
        params.min_id.as_deref(),
        params.since_id.as_deref(),
        &state.instance_domain,
        &format!("/api/v1/timelines/tag/{hashtag}"),
    );

    Ok((response_headers, Json(statuses)))
}

pub async fn link(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<LinkParams>,
) -> Result<impl IntoResponse, StatusCode> {
    let limit = params.limit.min(40);
    let languages = resolve_languages(&account, &headers);
    observe::language_requested(&languages);

    let filters = QueryFilters {
        language: languages,
        link: Some(params.url),
        ..Default::default()
    };

    let bound = state::providers::find_sources(&state.pool, "timelines/link").await;
    let sources = bound
        .into_iter()
        .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

    let feed = Feed::builder()
        .name("timelines/link")
        .sources(sources, 100)
        .score(Diversity::new(0.1, |post: &Post| {
            post.author.handle.clone()
        }))
        .build();

    let result = feed.execute(POOL_SIZE, &()).await;
    let posts: Vec<Post> = result.items.into_iter().map(|c| c.item).collect();
    let statuses = crate::commonfeed::posts_to_statuses(&state.pool, posts).await;

    let (statuses, response_headers) = paginate_statuses(
        statuses,
        limit,
        params.max_id.as_deref(),
        params.min_id.as_deref(),
        params.since_id.as_deref(),
        &state.instance_domain,
        "/api/v1/timelines/link",
    );

    Ok((response_headers, Json(statuses)))
}
