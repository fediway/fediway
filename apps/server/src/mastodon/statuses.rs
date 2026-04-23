//! `Status` response builders and Mastodon keyset pagination.

use std::collections::HashMap;

use axum::http::{HeaderMap, HeaderValue, header};
use common::ids::{AccountId, StatusId};
use common::paperclip::MediaConfig;
use common::types::Post;
use mastodon::Status;
use sources::mastodon::FeedItem;
use sqlx::PgPool;
use state::statuses::{PostMapping, fetch_by_ids};

enum ItemRef {
    Local(StatusId),
    Remote(usize),
}

pub async fn to_statuses(
    db: &PgPool,
    instance_domain: &str,
    media: &MediaConfig,
    items: Vec<FeedItem>,
    viewer: Option<AccountId>,
) -> Result<Vec<Status>, state::Error> {
    // A CommonFeed post already resolved into Mastodon's `statuses` table is
    // functionally local: Mastodon holds canonical content, counters, and
    // per-user state. Serving it from the cached `post_data` blob would lose
    // favourited/bookmarked/reblogged flags and return stale counters. The
    // upfront batch lookup lets the existing Local branch carry the Mastodon
    // id through `fetch_by_ids`.
    let provider_pairs: Vec<(String, i64)> = items
        .iter()
        .filter_map(|item| match item {
            FeedItem::Remote { post } => match (&post.provider_domain, post.provider_id) {
                (Some(domain), Some(remote_id)) => Some((domain.clone(), remote_id)),
                _ => None,
            },
            FeedItem::Local { .. } => None,
        })
        .collect();

    let resolved_map = state::statuses::find_mastodon_ids_by_provider(db, &provider_pairs).await?;

    let mut refs: Vec<ItemRef> = Vec::with_capacity(items.len());
    let mut local_ids: Vec<StatusId> = Vec::new();
    let mut remote_posts: Vec<Post> = Vec::new();
    for item in items {
        match item {
            FeedItem::Local { id } => {
                refs.push(ItemRef::Local(id));
                local_ids.push(id);
            }
            FeedItem::Remote { post } => {
                let promoted = match (&post.provider_domain, post.provider_id) {
                    (Some(domain), Some(remote_id)) => {
                        resolved_map.get(&(domain.clone(), remote_id)).copied()
                    }
                    _ => None,
                };
                if let Some(mastodon_id) = promoted {
                    refs.push(ItemRef::Local(mastodon_id));
                    local_ids.push(mastodon_id);
                } else {
                    refs.push(ItemRef::Remote(remote_posts.len()));
                    remote_posts.push(*post);
                }
            }
        }
    }

    let (local_result, remote_statuses) = tokio::join!(
        fetch_by_ids(db, instance_domain, media, &local_ids, viewer),
        from_posts(db, instance_domain, remote_posts),
    );
    let local_statuses = local_result?;

    let local_by_id: HashMap<StatusId, Status> = local_statuses
        .into_iter()
        .filter_map(|s| s.id.parse::<i64>().ok().map(|id| (StatusId(id), s)))
        .collect();
    let mut remote_by_idx: HashMap<usize, Status> =
        remote_statuses.into_iter().enumerate().collect();

    Ok(refs
        .into_iter()
        .filter_map(|r| match r {
            ItemRef::Local(id) => local_by_id.get(&id).cloned(),
            ItemRef::Remote(idx) => remote_by_idx.remove(&idx),
        })
        .collect())
}

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
                header_url: None,
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
