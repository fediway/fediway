use axum::Json;
use axum::extract::{Path, Query, State};
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
use crate::observe;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct Params {
    #[serde(default = "default_limit")]
    limit: usize,
    #[serde(default)]
    offset: Option<String>,
}

#[derive(Deserialize)]
pub struct TagParams {
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

const POOL_SIZE: usize = 100;

fn link_header(
    domain: &str,
    path: &str,
    cursor: Option<&String>,
) -> Option<(header::HeaderName, HeaderValue)> {
    let cursor = cursor?;
    let value = format!("<https://{domain}{path}?offset={cursor}>; rel=\"next\"");
    HeaderValue::from_str(&value)
        .ok()
        .map(|v| (header::LINK, v))
}

pub async fn home(
    account: Account,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<impl IntoResponse, StatusCode> {
    let handler_start = std::time::Instant::now();
    metrics::counter!("fediway_home_requests_total").increment(1);

    let limit = params.limit.min(40);
    let languages = resolve_languages(&Some(account.clone()), &headers);

    let filters = QueryFilters {
        language: languages,
        ..Default::default()
    };

    let vector_start = std::time::Instant::now();
    let user_vector = state::orbit::load_vector(&state.pool, account.id).await;
    metrics::histogram!("fediway_home_vector_load_duration_seconds")
        .record(vector_start.elapsed().as_secs_f64());

    let (recommended_pool, trending_pool) = if let Some((_vector, count)) = &user_vector {
        metrics::counter!("fediway_home_vector_loaded_total", "result" => "found").increment(1);
        let confidence = (f64::from(i32::try_from(*count).unwrap_or(i32::MAX)) / 50.0).min(1.0);
        metrics::histogram!("fediway_home_confidence").record(confidence);
        #[allow(clippy::cast_sign_loss)]
        let rec = (confidence * 60.0) as usize;
        (rec, POOL_SIZE - rec)
    } else {
        metrics::counter!("fediway_home_vector_loaded_total", "result" => "cold_start")
            .increment(1);
        (0, POOL_SIZE)
    };

    #[allow(clippy::cast_precision_loss)]
    let recommended_pool_f64 = recommended_pool as f64;
    #[allow(clippy::cast_precision_loss)]
    let trending_pool_f64 = trending_pool as f64;
    metrics::histogram!("fediway_home_recommended_pool").record(recommended_pool_f64);
    metrics::histogram!("fediway_home_trending_pool").record(trending_pool_f64);

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

    let posts: Vec<Post> = page.items.into_iter().map(|c| c.item).collect();
    let statuses = crate::commonfeed::posts_to_statuses(&state.pool, posts).await;

    #[allow(clippy::cast_precision_loss)]
    metrics::histogram!("fediway_home_results").record(statuses.len() as f64);

    let mut response_headers = HeaderMap::new();
    if let Some((key, value)) = link_header(
        &state.instance_domain,
        "/api/v1/timelines/home",
        page.cursor.as_ref(),
    ) {
        response_headers.insert(key, value);
    }

    metrics::histogram!("fediway_home_duration_seconds")
        .record(handler_start.elapsed().as_secs_f64());

    Ok((response_headers, Json(statuses)))
}

pub async fn tag(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(hashtag): Path<String>,
    Query(params): Query<TagParams>,
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

    let posts: Vec<Post> = result.items.into_iter().map(|c| c.item).collect();
    let statuses = crate::commonfeed::posts_to_statuses(&state.pool, posts).await;

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

    let posts: Vec<Post> = result.items.into_iter().map(|c| c.item).collect();
    let statuses = crate::commonfeed::posts_to_statuses(&state.pool, posts).await;

    Ok(Json(statuses))
}
