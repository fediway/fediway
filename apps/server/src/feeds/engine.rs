pub struct Page<T> {
    pub items: Vec<T>,
    pub cursor: Option<String>,
    pub has_more: bool,
}

#[must_use]
pub fn paginate<T>(items: Vec<T>, cursor: Option<&str>, limit: usize) -> Page<T> {
    let total = items.len();
    let offset = cursor
        .and_then(|c| c.parse::<usize>().ok())
        .unwrap_or(0)
        .min(total);
    let end = offset.saturating_add(limit).min(total);
    let has_more = end < total;
    Page {
        items: items.into_iter().skip(offset).take(end - offset).collect(),
        cursor: if has_more {
            Some(end.to_string())
        } else {
            None
        },
        has_more,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn first_page() {
        let page = paginate((1..=10).collect::<Vec<i32>>(), None, 4);
        assert_eq!(page.items, vec![1, 2, 3, 4]);
        assert_eq!(page.cursor.as_deref(), Some("4"));
        assert!(page.has_more);
    }

    #[test]
    fn with_cursor() {
        let page = paginate((1..=10).collect::<Vec<i32>>(), Some("4"), 4);
        assert_eq!(page.items, vec![5, 6, 7, 8]);
        assert_eq!(page.cursor.as_deref(), Some("8"));
        assert!(page.has_more);
    }

    #[test]
    fn last_page() {
        let page = paginate((1..=10).collect::<Vec<i32>>(), Some("8"), 4);
        assert_eq!(page.items, vec![9, 10]);
        assert!(page.cursor.is_none());
        assert!(!page.has_more);
    }

    #[test]
    fn cursor_past_end() {
        let page = paginate((1..=10).collect::<Vec<i32>>(), Some("100"), 4);
        assert!(page.items.is_empty());
        assert!(page.cursor.is_none());
        assert!(!page.has_more);
    }

    #[test]
    fn invalid_cursor_falls_back_to_zero() {
        let page = paginate((1..=10).collect::<Vec<i32>>(), Some("not-a-number"), 4);
        assert_eq!(page.items, vec![1, 2, 3, 4]);
        assert_eq!(page.cursor.as_deref(), Some("4"));
    }
}
