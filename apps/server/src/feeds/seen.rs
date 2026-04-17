use std::collections::HashSet;
use std::time::Duration;

use state::cache::Cache;

const TTL: Duration = Duration::from_secs(60 * 60);
const CAP: usize = 500;

fn key(user_id: i64) -> String {
    format!("home_seen:{user_id}")
}

pub async fn load(cache: &Cache, user_id: i64) -> HashSet<String> {
    cache
        .get::<Vec<String>>(&key(user_id))
        .await
        .unwrap_or_default()
        .into_iter()
        .collect()
}

pub async fn extend(cache: &Cache, user_id: i64, new: &[String]) {
    if new.is_empty() {
        return;
    }
    let k = key(user_id);
    let mut urls = cache.get::<Vec<String>>(&k).await.unwrap_or_default();
    urls.extend_from_slice(new);
    if urls.len() > CAP {
        let drop = urls.len() - CAP;
        urls.drain(..drop);
    }
    cache.set(&k, &urls, TTL).await;
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ids(values: &[&str]) -> Vec<String> {
        values.iter().map(|&s| s.to_owned()).collect()
    }

    #[tokio::test]
    async fn load_empty_key_returns_empty_set() {
        let cache = Cache::in_memory();
        let seen = load(&cache, 1).await;
        assert!(seen.is_empty());
    }

    #[tokio::test]
    async fn extend_stores_new_ids() {
        let cache = Cache::in_memory();
        extend(&cache, 1, &ids(&["a", "b"])).await;
        let seen = load(&cache, 1).await;
        assert_eq!(seen.len(), 2);
        assert!(seen.contains("a"));
        assert!(seen.contains("b"));
    }

    #[tokio::test]
    async fn extend_appends_to_existing() {
        let cache = Cache::in_memory();
        extend(&cache, 1, &ids(&["a", "b"])).await;
        extend(&cache, 1, &ids(&["c"])).await;
        let seen = load(&cache, 1).await;
        assert_eq!(seen.len(), 3);
        assert!(seen.contains("c"));
    }

    #[tokio::test]
    async fn extend_drops_oldest_over_cap() {
        let cache = Cache::in_memory();
        let initial: Vec<String> = (0..CAP).map(|i| format!("old-{i}")).collect();
        extend(&cache, 1, &initial).await;
        extend(&cache, 1, &ids(&["new"])).await;
        let seen = load(&cache, 1).await;
        assert_eq!(seen.len(), CAP);
        assert!(seen.contains("new"));
        assert!(!seen.contains("old-0"));
    }

    #[tokio::test]
    async fn extend_empty_input_is_noop() {
        let cache = Cache::in_memory();
        extend(&cache, 1, &ids(&["a"])).await;
        extend(&cache, 1, &[]).await;
        let seen = load(&cache, 1).await;
        assert_eq!(seen.len(), 1);
    }

    #[tokio::test]
    async fn seen_is_per_user() {
        let cache = Cache::in_memory();
        extend(&cache, 1, &ids(&["a"])).await;
        extend(&cache, 2, &ids(&["b"])).await;
        let seen_1 = load(&cache, 1).await;
        let seen_2 = load(&cache, 2).await;
        assert!(seen_1.contains("a"));
        assert!(!seen_1.contains("b"));
        assert!(seen_2.contains("b"));
        assert!(!seen_2.contains("a"));
    }
}
