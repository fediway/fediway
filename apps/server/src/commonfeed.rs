use std::collections::HashMap;

use common::types::Post;
use mastodon::Status;
use sqlx::PgPool;
use state::statuses::PostMapping;

/// Maps `CommonFeed` posts to Mastodon statuses with stable snowflake IDs.
/// Posts with `provider_id` get a snowflake via `commonfeed_statuses`.
/// Posts without `provider_id` fall back to URL-based identity.
pub async fn posts_to_statuses(db: &PgPool, posts: Vec<Post>) -> Vec<Status> {
    let mut mappings = Vec::new();
    let mut serialized = Vec::new();

    for post in &posts {
        if let (Some(domain), Some(remote_id)) = (&post.provider_domain, post.provider_id) {
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
            let status_id = post
                .provider_domain
                .as_ref()
                .zip(post.provider_id)
                .and_then(|(domain, remote_id)| id_map.get(&(domain.clone(), remote_id)))
                .map_or_else(|| post.url.clone(), ToString::to_string);

            Status::from_post(post, status_id)
        })
        .collect()
}
