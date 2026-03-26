use axum::Json;
use axum::extract::{Query, State};
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

const POOL_SIZE: usize = 100;

fn link_header(cursor: Option<&String>) -> Option<(header::HeaderName, HeaderValue)> {
    let cursor = cursor?;
    let value = format!("</api/v1/timelines/home?offset={cursor}>; rel=\"next\"");
    HeaderValue::from_str(&value)
        .ok()
        .map(|v| (header::LINK, v))
}

pub async fn handle(
    account: Account,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<impl IntoResponse, StatusCode> {
    let limit = params.limit.min(40);
    let languages = resolve_languages(&Some(account.clone()), &headers);

    let filters = QueryFilters {
        language: languages,
        ..Default::default()
    };

    let user_vector = state::orbit::load_vector(&state.pool, account.id).await;

    let (recommended_pool, trending_pool) = match &user_vector {
        Some((_vector, count)) => {
            let confidence = (f64::from(i32::try_from(*count).unwrap_or(i32::MAX)) / 50.0).min(1.0);
            #[allow(clippy::cast_sign_loss)]
            let rec = (confidence * 60.0) as usize;
            (rec, POOL_SIZE - rec)
        }
        None => (0, POOL_SIZE),
    };

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
    let page = result.paginate(
        limit,
        &feed::cursor::Offset::parse(params.offset.as_deref()),
    );

    let statuses: Vec<Status> = page
        .items
        .into_iter()
        .map(|c| Status::from(c.item))
        .collect();

    let mut response_headers = HeaderMap::new();
    if let Some((key, value)) = link_header(page.cursor.as_ref()) {
        response_headers.insert(key, value);
    }

    Ok((response_headers, Json(statuses)))
}
