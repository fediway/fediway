use axum::http::HeaderMap;
use axum::http::header::ACCEPT_LANGUAGE;

use crate::auth::Account;

/// Resolve preferred languages from the authenticated account or Accept-Language header.
#[must_use]
pub fn resolve_languages(account: Option<&Account>, headers: &HeaderMap) -> Vec<String> {
    match account {
        Some(a) if !a.chosen_languages.is_empty() => a.chosen_languages.clone(),
        _ => parse_accept_language(headers),
    }
}

pub fn parse_accept_language(headers: &HeaderMap) -> Vec<String> {
    let Some(header) = headers.get(ACCEPT_LANGUAGE).and_then(|v| v.to_str().ok()) else {
        return Vec::new();
    };

    let mut langs: Vec<(String, f32)> = header
        .split(',')
        .filter_map(|entry| {
            let entry = entry.trim();
            let (lang, quality) = match entry.split_once(";q=") {
                Some((l, q)) => (l.trim(), q.trim().parse::<f32>().unwrap_or(0.0)),
                None => (entry, 1.0),
            };

            // Take the primary language tag (e.g. "en" from "en-US")
            let primary = lang.split('-').next()?;
            if primary.is_empty() || primary == "*" {
                return None;
            }

            Some((primary.to_lowercase(), quality))
        })
        .collect();

    // Sort by quality descending, deduplicate
    langs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    langs.dedup_by(|a, b| a.0 == b.0);
    langs.into_iter().map(|(lang, _)| lang).collect()
}

#[cfg(test)]
mod tests {
    use axum::http::HeaderValue;

    use super::*;

    fn headers_with(value: &str) -> HeaderMap {
        let mut headers = HeaderMap::new();
        headers.insert(ACCEPT_LANGUAGE, HeaderValue::from_str(value).unwrap());
        headers
    }

    #[test]
    fn parses_single_language() {
        assert_eq!(parse_accept_language(&headers_with("en")), vec!["en"]);
    }

    #[test]
    fn parses_multiple_languages_with_quality() {
        assert_eq!(
            parse_accept_language(&headers_with("de, en;q=0.9, fr;q=0.8")),
            vec!["de", "en", "fr"],
        );
    }

    #[test]
    fn extracts_primary_tag() {
        assert_eq!(
            parse_accept_language(&headers_with("en-US, de-DE;q=0.9")),
            vec!["en", "de"],
        );
    }

    #[test]
    fn ignores_wildcard() {
        assert_eq!(
            parse_accept_language(&headers_with("en, *;q=0.1")),
            vec!["en"]
        );
    }

    #[test]
    fn returns_empty_without_header() {
        assert!(parse_accept_language(&HeaderMap::new()).is_empty());
    }

    #[test]
    fn handles_quality_sorting() {
        assert_eq!(
            parse_accept_language(&headers_with("fr;q=0.5, en;q=0.9, de;q=0.7")),
            vec!["en", "de", "fr"],
        );
    }
}
