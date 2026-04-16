use axum::extract::{Query, State};
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
use serde::Deserialize;

use crate::auth::Account;
use crate::feeds::trend_feed;
use crate::feeds::{TrendingLinksFeed, TrendingStatusesFeed, TrendingTagsFeed};
use crate::routes::mastodon::extract::request_filters;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct Params {
    #[serde(default = "default_limit")]
    limit: usize,
    #[serde(default)]
    offset: Option<String>,
}

const fn default_limit() -> usize {
    20
}

pub async fn statuses(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<impl IntoResponse, StatusCode> {
    let feed = TrendingStatusesFeed::new(&state, request_filters(account.as_ref(), &headers)).await;
    Ok(trend_feed::serve(
        &state,
        &feed,
        params.offset.as_deref(),
        params.limit.min(40),
    )
    .await)
}

pub async fn tags(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<impl IntoResponse, StatusCode> {
    let feed = TrendingTagsFeed::new(&state, request_filters(account.as_ref(), &headers)).await;
    Ok(trend_feed::serve(
        &state,
        &feed,
        params.offset.as_deref(),
        params.limit.min(40),
    )
    .await)
}

pub async fn links(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<impl IntoResponse, StatusCode> {
    let feed = TrendingLinksFeed::new(&state, request_filters(account.as_ref(), &headers)).await;
    Ok(trend_feed::serve(
        &state,
        &feed,
        params.offset.as_deref(),
        params.limit.min(40),
    )
    .await)
}
