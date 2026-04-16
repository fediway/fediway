use axum::extract::{Path, Query, State};
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
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
    let filters = request_filters(Some(&account), &headers);
    let feed = HomeFeed::new(&state, account.id, filters).await;
    Ok(feed.serve(&state, &params).await)
}

pub async fn tag(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(hashtag): Path<String>,
    Query(params): Query<TimelineParams>,
) -> Result<impl IntoResponse, StatusCode> {
    let filters = request_filters(account.as_ref(), &headers);
    let feed = TagTimelineFeed::new(&state, account.as_ref(), filters, hashtag).await;
    Ok(feed.serve(&state, &params).await)
}

pub async fn link(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<LinkParams>,
) -> Result<impl IntoResponse, StatusCode> {
    let filters = request_filters(account.as_ref(), &headers);
    let feed = LinkTimelineFeed::new(&state, account.as_ref(), filters, params.url).await;
    Ok(feed.serve(&state, &params.timeline).await)
}
