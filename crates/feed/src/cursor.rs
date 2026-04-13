use crate::candidate::Candidate;
use crate::pipeline::Page;

/// Cursor-based pagination for pipeline results.
///
/// Each implementation owns its decoded state and controls how items
/// are sliced into a page. Construct the cursor from the raw input,
/// then pass it to `PipelineResult::paginate`.
pub trait Cursor<Item> {
    /// Extract a page of at most `limit` items from the candidate list.
    fn paginate(&self, items: Vec<Candidate<Item>>, limit: usize) -> Page<Item>;
}

/// Offset-based cursor for stable, pre-ranked result sets.
///
/// Parses a raw offset string at construction and slices by position.
pub struct Offset {
    offset: usize,
}

impl Offset {
    #[must_use]
    pub fn parse(raw: Option<&str>) -> Self {
        Self {
            offset: raw.and_then(|c| c.parse().ok()).unwrap_or(0),
        }
    }
}

impl<Item> Cursor<Item> for Offset {
    fn paginate(&self, items: Vec<Candidate<Item>>, limit: usize) -> Page<Item> {
        let len = items.len();
        let start = self.offset.min(len);
        let end = (start + limit).min(len);
        let has_more = end < len;

        Page {
            items: items.into_iter().skip(start).take(end - start).collect(),
            cursor: if has_more {
                Some(end.to_string())
            } else {
                None
            },
            has_more,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn items(n: usize) -> Vec<Candidate<String>> {
        (0..n)
            .map(|i| {
                let mut c = Candidate::new(format!("item_{i}"), "test");
                c.score = (n - i) as f64;
                c
            })
            .collect()
    }

    #[test]
    fn first_page() {
        let page = Offset::parse(None).paginate(items(5), 2);
        assert_eq!(page.items.len(), 2);
        assert_eq!(page.items[0].item, "item_0");
        assert!(page.has_more);
        assert_eq!(page.cursor.as_deref(), Some("2"));
    }

    #[test]
    fn second_page() {
        let page = Offset::parse(Some("2")).paginate(items(5), 2);
        assert_eq!(page.items.len(), 2);
        assert_eq!(page.items[0].item, "item_2");
        assert!(page.has_more);
        assert_eq!(page.cursor.as_deref(), Some("4"));
    }

    #[test]
    fn last_page() {
        let page = Offset::parse(Some("4")).paginate(items(5), 2);
        assert_eq!(page.items.len(), 1);
        assert!(!page.has_more);
        assert!(page.cursor.is_none());
    }

    #[test]
    fn beyond_end() {
        let page = Offset::parse(Some("100")).paginate(items(2), 10);
        assert!(page.items.is_empty());
        assert!(!page.has_more);
    }

    #[test]
    fn invalid_cursor_starts_at_zero() {
        let page = Offset::parse(Some("garbage")).paginate(items(3), 2);
        assert_eq!(page.items[0].item, "item_0");
        assert!(page.has_more);
    }

    #[test]
    fn empty_items() {
        let page: Page<String> = Offset::parse(None).paginate(Vec::new(), 20);
        assert!(page.items.is_empty());
        assert!(!page.has_more);
    }
}
