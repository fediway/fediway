use crate::state::AppState;
use axum::Json;
use axum::extract::{Path, Query, State};
use axum::http::{HeaderMap, StatusCode};
use common::types::Post;
use feed::feed::Feed;
use feed::scorer::Diversity;
use mastodon::Status;
use serde::Deserialize;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::types::QueryFilters;

use crate::auth::Account;
use crate::language::resolve_languages;
use crate::observe;

#[derive(Deserialize)]
pub struct Params {
    #[serde(default = "default_limit")]
    limit: usize,
}

#[derive(Deserialize)]
pub struct LinkParams {
    url: String,
    #[serde(default = "default_limit")]
    limit: usize,
}

const fn default_limit() -> usize {
    20
}

pub async fn tag(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(hashtag): Path<String>,
    Query(params): Query<Params>,
) -> Result<Json<Vec<Status>>, StatusCode> {
    let limit = params.limit.min(40);
    let languages = resolve_languages(&account, &headers);
    observe::language_requested(&languages);

    let filters = QueryFilters {
        language: languages,
        tag: Some(hashtag),
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

    let result = feed.execute(limit, &()).await;

    let statuses: Vec<Status> = result
        .items
        .into_iter()
        .map(|c| Status::from(c.item))
        .collect();

    Ok(Json(statuses))
}

pub async fn link(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<LinkParams>,
) -> Result<Json<Vec<Status>>, StatusCode> {
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

    let result = feed.execute(limit, &()).await;

    let statuses: Vec<Status> = result
        .items
        .into_iter()
        .map(|c| Status::from(c.item))
        .collect();

    Ok(Json(statuses))
}
