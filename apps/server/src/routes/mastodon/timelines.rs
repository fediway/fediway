use axum::Json;
use axum::extract::{Path, Query, State};
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
use common::types::Post;
use feed::Feed;
use serde::Deserialize;

use crate::auth::Account;
use crate::feeds::{HomeFeed, LinkTimelineFeed, TagTimelineFeed, TimelineFeed, TimelineParams};
use crate::routes::mastodon::extract::request_filters;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct LinkParams {
    url: String,
    #[serde(flatten)]
    timeline: TimelineParams,
}

pub async fn home(
    account: Account,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<TimelineParams>,
) -> Result<impl IntoResponse, StatusCode> {
    let handler_start = std::time::Instant::now();
    metrics::counter!("fediway_home_requests_total").increment(1);

    let filters = request_filters(Some(&account), &headers);
    let feed = HomeFeed::new(&state, &account, filters).await;
    let candidates = feed.collect().await;

    let posts: Vec<Post> = candidates.into_iter().map(|c| c.item).collect();
    let statuses = crate::mastodon::statuses::from_posts(&state.pool, posts).await;

    let (statuses, response_headers) = crate::mastodon::statuses::paginate(
        statuses,
        params.limit.min(40),
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
    Query(params): Query<TimelineParams>,
) -> Result<impl IntoResponse, StatusCode> {
    let filters = request_filters(account.as_ref(), &headers);
    let feed = TagTimelineFeed::new(&state, filters, hashtag).await;
    Ok(feed.serve(&state, &params).await)
}

pub async fn link(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<LinkParams>,
) -> Result<impl IntoResponse, StatusCode> {
    let filters = request_filters(account.as_ref(), &headers);
    let feed = LinkTimelineFeed::new(&state, filters, params.url).await;
    Ok(feed.serve(&state, &params.timeline).await)
}
