//! `Status` response builders and Mastodon keyset pagination.

use std::collections::HashMap;

use axum::http::{HeaderMap, HeaderValue, header};
use common::types::Post;
use mastodon::Status;
use sqlx::PgPool;
use state::statuses::PostMapping;

/// Posts are resolved to Mastodon status IDs by provenance:
///
/// - Local (`provider_domain == instance_domain`) → `provider_id` used
///   directly as the status ID. Native Mastodon content already has a
///   stable snowflake; no mapping table insert.
/// - Remote `CommonFeed` (`provider_domain` set and not local) → mapped
///   through `commonfeed_statuses` to get a local snowflake. The
///   mapping inserts the post on first sighting so `/api/v1/statuses/{id}`
///   can resolve it on detail requests.
/// - No provenance → URL fallback (resilient for malformed input).
///
/// A batch snowflake lookup failure degrades remote posts to URL
/// identity rather than failing the request.
pub async fn from_posts(db: &PgPool, instance_domain: &str, posts: Vec<Post>) -> Vec<Status> {
    let mut mappings = Vec::new();
    let mut serialized = Vec::new();

    for post in &posts {
        if let (Some(domain), Some(remote_id)) = (&post.provider_domain, post.provider_id)
            && domain != instance_domain
        {
            serialized.push(serde_json::to_value(post).unwrap_or_default());
            mappings.push((
                domain.as_str(),
                remote_id,
                post.url.as_str(),
                post.uri.as_deref().unwrap_or(&post.url),
            ));
        }
    }

    let post_mappings: Vec<PostMapping<'_>> = mappings
        .iter()
        .zip(&serialized)
        .map(|((domain, remote_id, url, uri), data)| PostMapping {
            provider_domain: domain,
            remote_id: *remote_id,
            post_url: url,
            post_uri: uri,
            post_data: data,
        })
        .collect();

    let id_map = state::statuses::map_posts(db, &post_mappings)
        .await
        .unwrap_or_else(|e| {
            tracing::warn!(error = %e, "batch snowflake mapping failed");
            HashMap::new()
        });

    posts
        .into_iter()
        .map(|post| {
            let status_id = match (&post.provider_domain, post.provider_id) {
                (Some(domain), Some(id)) if domain == instance_domain => id.to_string(),
                (Some(domain), Some(remote_id)) => id_map
                    .get(&(domain.clone(), remote_id))
                    .map_or_else(|| post.url.clone(), ToString::to_string),
                _ => post.url.clone(),
            };

            Status::from_post(post, status_id)
        })
        .collect()
}

/// Status IDs are parsed as `i64` snowflakes; non-numeric IDs (e.g. the
/// URL-fallback identity from [`from_posts`]) are silently excluded
/// from the range check, since keyset pagination on URLs is meaningless.
pub fn paginate(
    mut statuses: Vec<Status>,
    limit: usize,
    max_id: Option<&str>,
    min_id: Option<&str>,
    since_id: Option<&str>,
    domain: &str,
    path: &str,
) -> (Vec<Status>, HeaderMap) {
    if let Some(max) = max_id.and_then(|s| s.parse::<i64>().ok()) {
        statuses.retain(|s| s.id.parse::<i64>().is_ok_and(|id| id < max));
    }
    if let Some(min) = min_id.and_then(|s| s.parse::<i64>().ok()) {
        statuses.retain(|s| s.id.parse::<i64>().is_ok_and(|id| id > min));
    }
    if let Some(since) = since_id.and_then(|s| s.parse::<i64>().ok()) {
        statuses.retain(|s| s.id.parse::<i64>().is_ok_and(|id| id > since));
    }

    statuses.truncate(limit);

    let mut headers = HeaderMap::new();
    if let (Some(last), Some(first)) = (statuses.last(), statuses.first()) {
        let next = format!("<https://{domain}{path}?max_id={}>; rel=\"next\"", last.id);
        let prev = format!("<https://{domain}{path}?min_id={}>; rel=\"prev\"", first.id);
        if let Ok(value) = HeaderValue::from_str(&format!("{next}, {prev}")) {
            headers.insert(header::LINK, value);
        }
    }

    (statuses, headers)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn status_with_id(id: &str) -> Status {
        let post = common::types::Post {
            provider_id: None,
            provider_domain: None,
            url: format!("https://example.com/{id}"),
            uri: None,
            content: String::new(),
            text: String::new(),
            author: common::types::Author {
                handle: "test".into(),
                display_name: "Test".into(),
                url: "https://example.com/@test".into(),
                avatar_url: None,
                emojis: vec![],
            },
            published_at: chrono::Utc::now(),
            language: None,
            sensitive: false,
            content_warning: None,
            media: vec![],
            engagement: common::types::Engagement {
                replies: 0,
                reposts: 0,
                likes: 0,
            },
            link: None,
            reply_to: None,
            quote: None,
            tags: vec![],
            emojis: vec![],
        };
        Status::from_post(post, id.to_string())
    }

    fn ids(statuses: &[Status]) -> Vec<&str> {
        statuses.iter().map(|s| s.id.as_str()).collect()
    }

    #[test]
    fn paginate_first_page() {
        let statuses = vec![
            status_with_id("50"),
            status_with_id("40"),
            status_with_id("30"),
            status_with_id("20"),
            status_with_id("10"),
        ];

        let (page, headers) =
            paginate(statuses, 3, None, None, None, "example.com", "/api/v1/test");

        assert_eq!(ids(&page), vec!["50", "40", "30"]);
        let link = headers.get(header::LINK).unwrap().to_str().unwrap();
        assert!(link.contains("max_id=30"));
        assert!(link.contains("min_id=50"));
    }

    #[test]
    fn paginate_with_max_id() {
        let statuses = vec![
            status_with_id("50"),
            status_with_id("40"),
            status_with_id("30"),
            status_with_id("20"),
            status_with_id("10"),
        ];

        let (page, _) = paginate(statuses, 3, Some("40"), None, None, "example.com", "/test");

        assert_eq!(ids(&page), vec!["30", "20", "10"]);
    }

    #[test]
    fn paginate_with_min_id() {
        let statuses = vec![
            status_with_id("50"),
            status_with_id("40"),
            status_with_id("30"),
            status_with_id("20"),
            status_with_id("10"),
        ];

        let (page, _) = paginate(statuses, 3, None, Some("20"), None, "example.com", "/test");

        assert_eq!(ids(&page), vec!["50", "40", "30"]);
    }

    #[test]
    fn paginate_with_since_id() {
        let statuses = vec![
            status_with_id("50"),
            status_with_id("40"),
            status_with_id("30"),
            status_with_id("20"),
            status_with_id("10"),
        ];

        let (page, _) = paginate(statuses, 2, None, None, Some("30"), "example.com", "/test");

        assert_eq!(ids(&page), vec!["50", "40"]);
    }

    #[test]
    fn paginate_empty_result() {
        let (page, headers) = paginate(vec![], 20, None, None, None, "example.com", "/test");

        assert!(page.is_empty());
        assert!(headers.get(header::LINK).is_none());
    }

    #[test]
    fn paginate_max_id_excludes_all() {
        let statuses = vec![status_with_id("50"), status_with_id("40")];

        let (page, _) = paginate(statuses, 20, Some("10"), None, None, "example.com", "/test");

        assert!(page.is_empty());
    }

    #[test]
    fn paginate_non_numeric_ids_ignored() {
        let statuses = vec![
            status_with_id("https://example.com/1"),
            status_with_id("50"),
            status_with_id("40"),
        ];

        let (page, _) = paginate(statuses, 3, Some("45"), None, None, "example.com", "/test");

        assert_eq!(ids(&page), vec!["40"]);
    }
}
