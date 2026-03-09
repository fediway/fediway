use axum::Json;
use axum::extract::{Query, State};
use axum::http::{HeaderMap, StatusCode};
use common::types::Post;
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

pub async fn statuses(
    account: Option<Account>,
    State(db): State<PgPool>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<Json<Vec<Post>>, StatusCode> {
    let limit = params.limit.min(40);

    let languages = match account {
        Some(ref a) if !a.chosen_languages.is_empty() => a.chosen_languages.clone(),
        _ => parse_accept_language(&headers),
    };

    let filters = QueryFilters {
        language: languages,
    };

    let providers = state::providers::find_for_capability(&db, "posts", "trending").await;
    let sources = providers
        .into_iter()
        .map(|p| PostsSource::new(p, "trending").with_filters(filters.clone()));

    let pipeline = Pipeline::builder()
        .sources(sources, 100)
        .score(Diversity::new(0.1, |post: &Post| post.author.id.clone()))
        .build();

    let candidates = pipeline.execute(limit, &()).await;
    let posts: Vec<Post> = candidates.into_iter().map(|c| c.item).collect();

    Ok(Json(posts))
}

pub async fn tags() -> StatusCode {
    StatusCode::OK
}
