use axum::Json;
use axum::extract::{Query, State};
use axum::http::{HeaderMap, HeaderValue, StatusCode, header};
use axum::response::IntoResponse;
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

pub async fn statuses(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<impl IntoResponse, StatusCode> {
    let handler_start = std::time::Instant::now();
    metrics::counter!("fediway_trends_requests_total", "resource" => "statuses").increment(1);

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
        .sources(sources, POOL_SIZE)
        .score(Diversity::new(0.1, |post: &Post| {
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

    #[allow(clippy::cast_precision_loss)]
    metrics::histogram!("fediway_trends_results", "resource" => "statuses")
        .record(statuses.len() as f64);

    let mut response_headers = HeaderMap::new();
    if let Some((key, value)) = link_header(
        &state.instance_domain,
        "/api/v1/trends/statuses",
        page.cursor.as_ref(),
    ) {
        response_headers.insert(key, value);
    }

    metrics::histogram!("fediway_trends_duration_seconds", "resource" => "statuses")
        .record(handler_start.elapsed().as_secs_f64());

    Ok((response_headers, Json(statuses)))
}

pub async fn tags(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<impl IntoResponse, StatusCode> {
    let handler_start = std::time::Instant::now();
    metrics::counter!("fediway_trends_requests_total", "resource" => "tags").increment(1);

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
        .sources(sources, POOL_SIZE)
        .score(Diversity::new(0.1, |tag: &Tag| tag.name.clone()))
        .build();

    let result = feed.execute(POOL_SIZE, &()).await;
    let page = result.paginate(
        limit,
        &feed::cursor::Offset::parse(params.offset.as_deref()),
    );

    let tags: Vec<MastodonTag> = page
        .items
        .into_iter()
        .map(|c| MastodonTag::from(c.item))
        .collect();

    #[allow(clippy::cast_precision_loss)]
    metrics::histogram!("fediway_trends_results", "resource" => "tags").record(tags.len() as f64);

    let mut response_headers = HeaderMap::new();
    if let Some((key, value)) = link_header(
        &state.instance_domain,
        "/api/v1/trends/tags",
        page.cursor.as_ref(),
    ) {
        response_headers.insert(key, value);
    }

    metrics::histogram!("fediway_trends_duration_seconds", "resource" => "tags")
        .record(handler_start.elapsed().as_secs_f64());

    Ok((response_headers, Json(tags)))
}

pub async fn links(
    account: Option<Account>,
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<Params>,
) -> Result<impl IntoResponse, StatusCode> {
    let handler_start = std::time::Instant::now();
    metrics::counter!("fediway_trends_requests_total", "resource" => "links").increment(1);

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
        .sources(sources, POOL_SIZE)
        .score(Diversity::new(0.1, |link: &Link| {
            link.provider_name.clone().unwrap_or_default()
        }))
        .build();

    let result = feed.execute(POOL_SIZE, &()).await;
    let page = result.paginate(
        limit,
        &feed::cursor::Offset::parse(params.offset.as_deref()),
    );

    let links: Vec<PreviewCard> = page
        .items
        .into_iter()
        .map(|c| PreviewCard::from(c.item))
        .collect();

    #[allow(clippy::cast_precision_loss)]
    metrics::histogram!("fediway_trends_results", "resource" => "links").record(links.len() as f64);

    let mut response_headers = HeaderMap::new();
    if let Some((key, value)) = link_header(
        &state.instance_domain,
        "/api/v1/trends/links",
        page.cursor.as_ref(),
    ) {
        response_headers.insert(key, value);
    }

    metrics::histogram!("fediway_trends_duration_seconds", "resource" => "links")
        .record(handler_start.elapsed().as_secs_f64());

    Ok((response_headers, Json(links)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn link_header_returns_absolute_url() {
        let cursor = Some("abc123".to_string());
        let (key, value) = link_header(
            "mastodon.social",
            "/api/v1/trends/statuses",
            cursor.as_ref(),
        )
        .unwrap();
        assert_eq!(key, header::LINK);
        assert_eq!(
            value.to_str().unwrap(),
            r#"<https://mastodon.social/api/v1/trends/statuses?offset=abc123>; rel="next""#,
        );
    }

    #[test]
    fn link_header_returns_none_without_cursor() {
        assert!(link_header("mastodon.social", "/api/v1/trends/statuses", None).is_none());
    }
}
