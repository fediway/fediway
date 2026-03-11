use crate::state::AppState;
use axum::Json;
use axum::extract::{Query, State};
use axum::http::{HeaderMap, StatusCode};
use common::types::{Link, Post, Tag};
use feed::feed::Feed;
use feed::scorer::Diversity;
use mastodon::{PreviewCard, Status, Tag as MastodonTag};
use serde::Deserialize;
use sources::commonfeed::links::LinksSource;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::tags::TagsSource;
use sources::commonfeed::types::QueryFilters;

use crate::auth::Account;
use crate::language::resolve_languages;
use crate::observe;

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
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<Json<Vec<Status>>, StatusCode> {
    let limit = params.limit.min(40);
    let languages = resolve_languages(&account, &headers);
    observe::language_requested(&languages);

    let filters = QueryFilters {
        language: languages,
        ..Default::default()
    };

    let bound = state::providers::find_sources(&state.pool, "trends/statuses").await;
    let sources = bound
        .into_iter()
        .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

    let feed = Feed::builder()
        .name("trends/statuses")
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

pub async fn tags(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<Json<Vec<MastodonTag>>, StatusCode> {
    let limit = params.limit.min(40);
    let languages = resolve_languages(&account, &headers);
    observe::language_requested(&languages);

    let filters = QueryFilters {
        language: languages,
        ..Default::default()
    };

    let bound = state::providers::find_sources(&state.pool, "trends/tags").await;
    let sources = bound
        .into_iter()
        .map(|b| TagsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

    let feed = Feed::builder()
        .name("trends/tags")
        .sources(sources, 100)
        .score(Diversity::new(0.1, |tag: &Tag| tag.name.clone()))
        .build();

    let result = feed.execute(limit, &()).await;

    let tags: Vec<MastodonTag> = result
        .items
        .into_iter()
        .map(|c| MastodonTag::from(c.item))
        .collect();

    Ok(Json(tags))
}

pub async fn links(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<Json<Vec<PreviewCard>>, StatusCode> {
    let limit = params.limit.min(40);
    let languages = resolve_languages(&account, &headers);
    observe::language_requested(&languages);

    let filters = QueryFilters {
        language: languages,
        ..Default::default()
    };

    let bound = state::providers::find_sources(&state.pool, "trends/links").await;
    let sources = bound
        .into_iter()
        .map(|b| LinksSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

    let feed = Feed::builder()
        .name("trends/links")
        .sources(sources, 100)
        .score(Diversity::new(0.1, |link: &Link| {
            link.provider_name.clone().unwrap_or_default()
        }))
        .build();

    let result = feed.execute(limit, &()).await;

    let links: Vec<PreviewCard> = result
        .items
        .into_iter()
        .map(|c| PreviewCard::from(c.item))
        .collect();

    Ok(Json(links))
}
