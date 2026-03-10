use axum::Json;
use axum::extract::{Query, State};
use axum::http::{HeaderMap, StatusCode};
use common::types::{Link, Post, Tag};
use mastodon::{PreviewCard, Status, Tag as MastodonTag};
use pipeline::pipeline::Pipeline;
use pipeline::scorer::Diversity;
use serde::Deserialize;
use sources::commonfeed::links::LinksSource;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::tags::TagsSource;
use sources::commonfeed::types::QueryFilters;
use sqlx::PgPool;

use crate::auth::Account;
use crate::language::resolve_languages;

#[derive(Deserialize)]
pub struct Params {
    #[serde(default = "default_limit")]
    limit: usize,
}

const fn default_limit() -> usize {
    20
}

pub async fn statuses(
    account: Option<Account>,
    State(db): State<PgPool>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<Json<Vec<Status>>, StatusCode> {
    let limit = params.limit.min(40);

    let filters = QueryFilters {
        language: resolve_languages(&account, &headers),
        ..Default::default()
    };

    let bound = state::providers::find_sources(&db, "trends/statuses").await;
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

pub async fn tags(
    account: Option<Account>,
    State(db): State<PgPool>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<Json<Vec<MastodonTag>>, StatusCode> {
    let limit = params.limit.min(40);

    let filters = QueryFilters {
        language: resolve_languages(&account, &headers),
        ..Default::default()
    };

    let bound = state::providers::find_sources(&db, "trends/tags").await;
    let sources = bound
        .into_iter()
        .map(|b| TagsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

    let pipeline = Pipeline::builder()
        .sources(sources, 100)
        .score(Diversity::new(0.1, |tag: &Tag| tag.name.clone()))
        .build();

    let candidates = pipeline.execute(limit, &()).await;
    let tags: Vec<MastodonTag> = candidates
        .into_iter()
        .map(|c| MastodonTag::from(c.item))
        .collect();

    Ok(Json(tags))
}

pub async fn links(
    account: Option<Account>,
    State(db): State<PgPool>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<Json<Vec<PreviewCard>>, StatusCode> {
    let limit = params.limit.min(40);

    let filters = QueryFilters {
        language: resolve_languages(&account, &headers),
        ..Default::default()
    };

    let bound = state::providers::find_sources(&db, "trends/links").await;
    let sources = bound
        .into_iter()
        .map(|b| LinksSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

    let pipeline = Pipeline::builder()
        .sources(sources, 100)
        .score(Diversity::new(0.1, |link: &Link| {
            link.provider_name.clone().unwrap_or_default()
        }))
        .build();

    let candidates = pipeline.execute(limit, &()).await;
    let links: Vec<PreviewCard> = candidates
        .into_iter()
        .map(|c| PreviewCard::from(c.item))
        .collect();

    Ok(Json(links))
}
