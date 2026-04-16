use std::sync::OnceLock;

use regex::Regex;

use crate::mention::Mention;
use crate::sanitize::sanitize_html;
use crate::tag::Tag;

const LINK_DISPLAY_MAX: usize = 30;

/// Formats local-origin plain text into Mastodon-compatible HTML.
///
/// Mirrors Mastodon's `TextFormatter`: linkifies URLs with invisible-span
/// truncation, wraps mentions in h-card microformat spans, converts
/// hashtags to tag links, and wraps paragraphs with `<p>` / `<br />`.
///
/// Reference: <https://github.com/mastodon/mastodon/blob/main/app/lib/text_formatter.rb>
#[must_use]
pub fn format_local(
    text: &str,
    mentions: &[Mention],
    tags: &[Tag],
    instance_domain: &str,
) -> String {
    let mut spans: Vec<(usize, usize, String)> = Vec::new();

    for m in url_regex().find_iter(text) {
        spans.push((m.start(), m.end(), shortened_link(m.as_str())));
    }

    for mention in mentions {
        let anchor = mention_html(mention);
        if let Some(domain) = mention.acct.split('@').nth(1) {
            let needle = format!("@{}@{domain}", mention.username);
            push_word_matches(text, &needle, &anchor, &mut spans);
        }
        let needle = format!("@{}", mention.username);
        push_word_matches(text, &needle, &anchor, &mut spans);
    }

    for tag in tags {
        let needle = format!("#{}", tag.name);
        let anchor = tag_html(tag, instance_domain);
        push_word_matches(text, &needle, &anchor, &mut spans);
    }

    spans.sort_by_key(|(start, end, _)| (*start, std::cmp::Reverse(*end)));
    let mut non_overlapping: Vec<(usize, usize, String)> = Vec::with_capacity(spans.len());
    for span in spans {
        if non_overlapping.last().is_none_or(|last| span.0 >= last.1) {
            non_overlapping.push(span);
        }
    }

    let mut out = String::with_capacity(text.len() + 32);
    let mut cursor = 0;
    for (start, end, anchor) in non_overlapping {
        out.push_str(&escape_text(&text[cursor..start]));
        out.push_str(&anchor);
        cursor = end;
    }
    out.push_str(&escape_text(&text[cursor..]));

    let paragraphs: Vec<String> = out
        .split("\n\n")
        .filter(|p| !p.is_empty())
        .map(|p| format!("<p>{}</p>", p.replace('\n', "<br />")))
        .collect();
    if paragraphs.is_empty() {
        "<p></p>".to_owned()
    } else {
        paragraphs.join("")
    }
}

/// Sanitizes remote-origin HTML for safe rendering.
///
/// Mirrors Mastodon's `HtmlAwareFormatter#reformat` + sanitizer
/// `add_attributes`: strips dangerous tags, converts unsupported h1-h6
/// elements to `<strong>`, and adds `target="_blank"` to all links.
///
/// Reference: <https://github.com/mastodon/mastodon/blob/main/app/lib/html_aware_formatter.rb>
#[must_use]
pub fn format_remote(html: &str) -> String {
    let preprocessed = heading_open_regex()
        .replace_all(html, "<p><strong>")
        .into_owned();
    let preprocessed = heading_close_regex()
        .replace_all(&preprocessed, "</strong></p>")
        .into_owned();
    sanitize_html(&preprocessed).replace("<a ", "<a target=\"_blank\" ")
}

/// Mirrors Mastodon's `TextFormatter.shortened_link`: hides the URL scheme
/// (and optional `www.`) via `<span class="invisible">`, truncates the
/// visible portion to [`LINK_DISPLAY_MAX`] chars with an `ellipsis` class.
///
/// Reference: <https://github.com/mastodon/mastodon/blob/main/app/lib/text_formatter.rb>
fn shortened_link(url: &str) -> String {
    let scheme_end = url.find("://").map_or(0, |i| i + 3);
    let after_scheme = &url[scheme_end..];
    let www = if after_scheme.starts_with("www.") {
        4
    } else {
        0
    };
    let prefix = &url[..scheme_end + www];
    let rest = &url[scheme_end + www..];

    let (display, suffix, class) = if rest.len() > LINK_DISPLAY_MAX {
        (
            &rest[..LINK_DISPLAY_MAX],
            &rest[LINK_DISPLAY_MAX..],
            "ellipsis",
        )
    } else {
        (rest, "", "")
    };

    format!(
        "<a href=\"{href}\" target=\"_blank\" rel=\"nofollow noopener noreferrer\" translate=\"no\">\
         <span class=\"invisible\">{prefix}</span>\
         <span class=\"{class}\">{display}</span>\
         <span class=\"invisible\">{suffix}</span>\
         </a>",
        href = escape_attr(url),
        prefix = escape_text(prefix),
        display = escape_text(display),
        suffix = escape_text(suffix),
    )
}

fn mention_html(m: &Mention) -> String {
    format!(
        "<span class=\"h-card\" translate=\"no\">\
         <a href=\"{url}\" class=\"u-url mention\">@<span>{acct}</span></a>\
         </span>",
        url = escape_attr(&m.url),
        acct = escape_text(&m.acct),
    )
}

fn tag_html(t: &Tag, instance_domain: &str) -> String {
    format!(
        "<a href=\"https://{instance_domain}/tags/{name}\" class=\"mention hashtag\" rel=\"tag\">\
         #<span>{display}</span>\
         </a>",
        name = escape_attr(&t.name),
        display = escape_text(&t.name),
    )
}

fn push_word_matches(
    text: &str,
    needle: &str,
    html: &str,
    spans: &mut Vec<(usize, usize, String)>,
) {
    if needle.len() < 2 {
        return;
    }
    let mut search_from = 0;
    while let Some(rel) = text[search_from..].find(needle) {
        let start = search_from + rel;
        let end = start + needle.len();
        let preceded_by_word = start > 0
            && text[..start]
                .chars()
                .next_back()
                .is_some_and(|c| c.is_alphanumeric() || c == '_' || c == '@' || c == '#');
        let followed_by_word = text[end..]
            .chars()
            .next()
            .is_some_and(|c| c.is_alphanumeric() || c == '_' || c == '@');
        if !preceded_by_word && !followed_by_word {
            spans.push((start, end, html.to_owned()));
        }
        search_from = end;
    }
}

fn url_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"https?://[^\s<>\x22\]]+").expect("valid regex"))
}

fn heading_open_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"<h[1-6][^>]*>").expect("valid regex"))
}

fn heading_close_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"</h[1-6]>").expect("valid regex"))
}

fn escape_text(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            _ => out.push(c),
        }
    }
    out
}

fn escape_attr(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            _ => out.push(c),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mention(username: &str, acct: &str, url: &str) -> Mention {
        Mention {
            id: "1".into(),
            username: username.into(),
            acct: acct.into(),
            url: url.into(),
        }
    }

    fn tag(name: &str) -> Tag {
        Tag {
            name: name.into(),
            url: format!("/tags/{name}"),
            history: Vec::new(),
        }
    }

    #[test]
    fn local_wraps_plain_text_in_paragraphs() {
        let html = format_local("hello world", &[], &[], "example.com");
        assert_eq!(html, "<p>hello world</p>");
    }

    #[test]
    fn local_converts_double_newline_to_paragraph_break() {
        let html = format_local("one\n\ntwo", &[], &[], "example.com");
        assert_eq!(html, "<p>one</p><p>two</p>");
    }

    #[test]
    fn local_converts_single_newline_to_br() {
        let html = format_local("one\ntwo", &[], &[], "example.com");
        assert_eq!(html, "<p>one<br />two</p>");
    }

    #[test]
    fn local_escapes_html_in_plain_text() {
        let html = format_local("<script>alert('xss')</script>", &[], &[], "example.com");
        assert!(html.contains("&lt;script&gt;"));
        assert!(!html.contains("<script>"));
    }

    #[test]
    fn local_linkifies_urls_with_invisible_spans() {
        let html = format_local("check https://example.com/path", &[], &[], "example.com");
        assert!(html.contains("class=\"invisible\""));
        assert!(html.contains("target=\"_blank\""));
        assert!(html.contains("rel=\"nofollow noopener noreferrer\""));
        assert!(html.contains("translate=\"no\""));
    }

    #[test]
    fn local_truncates_long_urls_with_ellipsis() {
        let html = format_local(
            "see https://example.com/very/long/path/to/article/page",
            &[],
            &[],
            "example.com",
        );
        assert!(html.contains("class=\"ellipsis\""));
    }

    #[test]
    fn local_short_url_has_no_ellipsis() {
        let html = format_local("see https://example.com/", &[], &[], "example.com");
        assert!(!html.contains("ellipsis"));
    }

    #[test]
    fn local_www_prefix_is_invisible() {
        let html = format_local("see https://www.example.com/page", &[], &[], "example.com");
        assert!(html.contains("<span class=\"invisible\">https://www.</span>"));
    }

    #[test]
    fn local_mentions_wrapped_in_hcard() {
        let m = mention("alice", "alice", "https://example.com/@alice");
        let html = format_local("hi @alice", &[m], &[], "example.com");
        assert!(html.contains("class=\"h-card\""));
        assert!(html.contains("translate=\"no\""));
        assert!(html.contains("class=\"u-url mention\""));
        assert!(html.contains("@<span>alice</span>"));
    }

    #[test]
    fn local_remote_mention_shows_full_acct() {
        let m = mention("bob", "bob@remote.example", "https://remote.example/@bob");
        let html = format_local("hi @bob@remote.example", &[m], &[], "example.com");
        assert!(html.contains("@<span>bob@remote.example</span>"));
    }

    #[test]
    fn local_hashtags_linked() {
        let t = tag("rust");
        let html = format_local("love #rust", &[], &[t], "example.com");
        assert!(html.contains("class=\"mention hashtag\""));
        assert!(html.contains("rel=\"tag\""));
        assert!(html.contains("#<span>rust</span>"));
        assert!(html.contains("https://example.com/tags/rust"));
    }

    #[test]
    fn local_empty_text_produces_empty_paragraph() {
        assert_eq!(format_local("", &[], &[], "example.com"), "<p></p>");
    }

    #[test]
    fn remote_sanitizes_html() {
        let html = "<p>hello</p><script>evil</script>";
        let result = format_remote(html);
        assert!(result.contains("<p>hello</p>"));
        assert!(!result.contains("script"));
    }

    #[test]
    fn remote_adds_target_blank_to_links() {
        let html = r#"<p><a href="https://example.com">link</a></p>"#;
        let result = format_remote(html);
        assert!(result.contains("target=\"_blank\""));
    }

    #[test]
    fn remote_converts_headings_to_strong() {
        let html = "<h1>Title</h1><p>body</p>";
        let result = format_remote(html);
        assert!(!result.contains("<h1>"));
        assert!(result.contains("<strong>"));
        assert!(result.contains("Title"));
    }

    #[test]
    fn remote_converts_all_heading_levels() {
        for level in 1..=6 {
            let html = format!("<h{level}>heading</h{level}>");
            let result = format_remote(&html);
            assert!(
                result.contains("<strong>heading</strong>"),
                "h{level} must convert to <strong>"
            );
        }
    }

    #[test]
    fn remote_preserves_existing_html_structure() {
        let html = r#"<p>hello <a href="https://example.com" class="mention">@user</a></p>"#;
        let result = format_remote(html);
        assert!(result.contains("class=\"mention\""));
        assert!(result.contains("hello"));
    }
}
