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
use crate::language::parse_accept_language;

#[derive(Deserialize)]
pub struct Params {
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

    let languages = match account {
        Some(ref a) if !a.chosen_languages.is_empty() => a.chosen_languages.clone(),
        _ => parse_accept_language(&headers),
    };

    let filters = QueryFilters {
        language: languages,
        tag: Some(hashtag),
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
