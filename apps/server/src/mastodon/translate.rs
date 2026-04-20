use std::collections::HashMap;
use std::sync::Arc;

use serde_json::Value;
use sqlx::PgPool;

use crate::auth::BearerToken;
use crate::mastodon::resolve::{ResolveError, Resolver};

/// Rewrites a snowflake-shaped request field to the resolved Mastodon local id.
///
/// `id` is mutated in place. Non-numeric ids and snowflakes without a cached
/// mapping are left untouched so that clients passing native Mastodon ids
/// (from the home timeline proxy path) still work.
pub async fn translate_request_id(
    resolver: &Arc<Resolver>,
    token: &BearerToken,
    id: &mut String,
) -> Result<(), ResolveError> {
    let Ok(snowflake) = id.parse::<i64>() else {
        return Ok(());
    };
    match resolver.resolve(snowflake, token).await {
        Ok(mastodon_id) => {
            *id = mastodon_id.to_string();
            Ok(())
        }
        Err(ResolveError::NotFound) => Ok(()),
        Err(e) => Err(e),
    }
}

/// Rewrites every `Mastodon local id → Fediway snowflake` reference in a
/// response status JSON value that has a mapping in `commonfeed_statuses`.
///
/// Walks `status.id`, `status.in_reply_to_id`, and recursively into the
/// `reblog` field (Mastodon only nests reblogs one level, but the recursion
/// is harmless if that invariant ever loosens). A single batched
/// `reverse_map` query covers all lookups per response.
pub async fn translate_response(pool: &PgPool, value: &mut Value) -> Result<(), state::Error> {
    let mut ids = Vec::with_capacity(4);
    collect_ids(value, &mut ids);

    if ids.is_empty() {
        return Ok(());
    }

    let map = state::statuses::reverse_map(pool, &ids).await?;
    if map.is_empty() {
        return Ok(());
    }

    apply_map(value, &map);
    Ok(())
}

fn collect_ids(value: &Value, out: &mut Vec<i64>) {
    push_numeric(value.get("id"), out);
    push_numeric(value.get("in_reply_to_id"), out);
    if let Some(reblog) = value.get("reblog")
        && !reblog.is_null()
    {
        collect_ids(reblog, out);
    }
    if let Some(quoted) = value.get("quote").and_then(|q| q.get("quoted_status"))
        && !quoted.is_null()
    {
        collect_ids(quoted, out);
    }
}

fn apply_map(value: &mut Value, map: &HashMap<i64, i64>) {
    rewrite_field(value, "id", map);
    rewrite_field(value, "in_reply_to_id", map);
    if let Some(reblog) = value.get_mut("reblog")
        && !reblog.is_null()
    {
        apply_map(reblog, map);
    }
    if let Some(quoted) = value
        .get_mut("quote")
        .and_then(|q| q.get_mut("quoted_status"))
        && !quoted.is_null()
    {
        apply_map(quoted, map);
    }
}

fn push_numeric(field: Option<&Value>, out: &mut Vec<i64>) {
    if let Some(s) = field.and_then(Value::as_str)
        && let Ok(n) = s.parse::<i64>()
    {
        out.push(n);
    }
}

fn rewrite_field(value: &mut Value, key: &str, map: &HashMap<i64, i64>) {
    let Some(field) = value.get_mut(key) else {
        return;
    };
    let Some(s) = field.as_str() else { return };
    let Ok(n) = s.parse::<i64>() else { return };
    if let Some(&snowflake) = map.get(&n) {
        *field = Value::String(snowflake.to_string());
    }
}
