use axum::Json;
use axum::extract::{Path, Query, State};
use axum::http::{HeaderMap, StatusCode};
use common::types::Post;
use mastodon::Status;
use pipeline::pipeline::Pipeline;
use pipeline::scorer::Diversity;
use serde::Deserialize;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::types::QueryFilters;
use sqlx::PgPool;

use crate::auth::Account;
use crate::language::resolve_languages;

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
    State(db): State<PgPool>,
    headers: HeaderMap,
    Path(hashtag): Path<String>,
    Query(params): Query<Params>,
) -> Result<Json<Vec<Status>>, StatusCode> {
    let limit = params.limit.min(40);

    let filters = QueryFilters {
        language: resolve_languages(&account, &headers),
        tag: Some(hashtag),
        ..Default::default()
    };

    let bound = state::providers::find_sources(&db, "timelines/tag").await;
    let sources = bound
        .into_iter()
        .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

    let pipeline = Pipeline::builder()
        .sources(sources, 100)
        .score(Diversity::new(0.1, |post: &Post| {
            post.author.handle.clone()
        }))
        .build();

    let candidates = pipeline.execute(limit, &()).await;
    let statuses: Vec<Status> = candidates
        .into_iter()
        .map(|c| Status::from(c.item))
        .collect();

    Ok(Json(statuses))
}

pub async fn link(
    account: Option<Account>,
    State(db): State<PgPool>,
    headers: HeaderMap,
    Query(params): Query<LinkParams>,
) -> Result<Json<Vec<Status>>, StatusCode> {
    let limit = params.limit.min(40);

    let filters = QueryFilters {
        language: resolve_languages(&account, &headers),
        link: Some(params.url),
        ..Default::default()
    };

    let bound = state::providers::find_sources(&db, "timelines/link").await;
    let sources = bound
        .into_iter()
        .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

    let pipeline = Pipeline::builder()
        .sources(sources, 100)
        .score(Diversity::new(0.1, |post: &Post| {
            post.author.handle.clone()
        }))
        .build();

    let candidates = pipeline.execute(limit, &()).await;
    let statuses: Vec<Status> = candidates
        .into_iter()
        .map(|c| Status::from(c.item))
        .collect();

    Ok(Json(statuses))
}
