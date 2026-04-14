use std::future::Future;
use std::time::Duration;

use serde::Serialize;
use serde::de::DeserializeOwned;

use crate::cache::Cache;

#[derive(Debug, Clone)]
pub struct Page<T> {
    pub items: Vec<T>,
    pub cursor: Option<String>,
    pub has_more: bool,
}

#[derive(Clone)]
pub struct FeedStore {
    cache: Cache,
    ttl: Duration,
}

impl FeedStore {
    #[must_use]
    pub fn new(cache: Cache, ttl: Duration) -> Self {
        Self { cache, ttl }
    }

    pub async fn page<T, F, Fut>(
        &self,
        key: &str,
        cursor: Option<&str>,
        limit: usize,
        build: F,
    ) -> Page<T>
    where
        T: Serialize + DeserializeOwned + Send + Sync,
        F: FnOnce() -> Fut + Send,
        Fut: Future<Output = Vec<T>> + Send,
    {
        let cached = if cursor.is_some() {
            self.cache.get::<Vec<T>>(key).await
        } else {
            None
        };

        let items = if let Some(items) = cached {
            items
        } else {
            let fresh = build().await;
            self.cache.set(key, &fresh, self.ttl).await;
            fresh
        };

        slice(items, cursor, limit)
    }
}

fn slice<T>(items: Vec<T>, cursor: Option<&str>, limit: usize) -> Page<T> {
    let total = items.len();
    let offset = cursor
        .and_then(|c| c.parse::<usize>().ok())
        .unwrap_or(0)
        .min(total);
    let end = offset.saturating_add(limit).min(total);
    let has_more = end < total;
    let next_cursor = if has_more {
        Some(end.to_string())
    } else {
        None
    };
    let page_items: Vec<T> = items.into_iter().skip(offset).take(end - offset).collect();
    Page {
        items: page_items,
        cursor: next_cursor,
        has_more,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slice_first_page() {
        let page = slice((1..=10).collect::<Vec<i32>>(), None, 4);
        assert_eq!(page.items, vec![1, 2, 3, 4]);
        assert_eq!(page.cursor.as_deref(), Some("4"));
        assert!(page.has_more);
    }

    #[test]
    fn slice_with_cursor() {
        let page = slice((1..=10).collect::<Vec<i32>>(), Some("4"), 4);
        assert_eq!(page.items, vec![5, 6, 7, 8]);
        assert_eq!(page.cursor.as_deref(), Some("8"));
        assert!(page.has_more);
    }

    #[test]
    fn slice_last_page_marks_no_more() {
        let page = slice((1..=10).collect::<Vec<i32>>(), Some("8"), 4);
        assert_eq!(page.items, vec![9, 10]);
        assert!(page.cursor.is_none());
        assert!(!page.has_more);
    }

    #[test]
    fn slice_cursor_past_end_returns_empty() {
        let page = slice((1..=10).collect::<Vec<i32>>(), Some("100"), 4);
        assert!(page.items.is_empty());
        assert!(page.cursor.is_none());
        assert!(!page.has_more);
    }

    #[test]
    fn slice_invalid_cursor_falls_back_to_zero() {
        let page = slice((1..=10).collect::<Vec<i32>>(), Some("not-a-number"), 4);
        assert_eq!(page.items, vec![1, 2, 3, 4]);
        assert_eq!(page.cursor.as_deref(), Some("4"));
    }
}
