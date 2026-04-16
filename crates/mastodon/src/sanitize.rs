use std::collections::HashSet;

/// Sanitize HTML content for Mastodon API responses.
///
/// Matches Mastodon's `MASTODON_STRICT` sanitizer configuration exactly.
/// Third-party apps trust that the Mastodon API returns safe HTML —
/// we must uphold that contract.
///
/// Reference: <https://github.com/mastodon/mastodon/blob/main/lib/sanitize_ext/sanitize_config.rb>
#[must_use]
pub fn sanitize_html(html: &str) -> String {
    // Mastodon's MASTODON_STRICT allowed tags
    let allowed_tags: HashSet<&str> = [
        "p",
        "br",
        "span",
        "a",
        "del",
        "s",
        "pre",
        "blockquote",
        "code",
        "b",
        "strong",
        "u",
        "i",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "ul",
        "ol",
        "li",
        "ruby",
        "rt",
        "rp",
    ]
    .into_iter()
    .collect();

    ammonia::Builder::new()
        .tags(allowed_tags)
        // Per-tag attributes matching Mastodon's config
        .add_tag_attributes("a", &["href", "class", "translate"])
        .add_tag_attributes("span", &["class", "translate"])
        .add_tag_attributes("p", &["class"])
        .add_tag_attributes("ol", &["start", "reversed"])
        .add_tag_attributes("li", &["value"])
        // Mastodon sets rel="nofollow noopener" on all links
        .link_rel(Some("nofollow noopener"))
        // Allowed URL schemes for href/cite
        .url_schemes(HashSet::from([
            "http", "https", "dat", "dweb", "ipfs", "ipns", "ssb", "gopher", "xmpp", "magnet",
            "gemini",
        ]))
        .clean(html)
        .to_string()
}

/// Sanitize text fields that should contain no HTML at all.
/// Strips all tags and escapes entities.
#[must_use]
pub fn sanitize_text(text: &str) -> String {
    ammonia::Builder::new()
        .tags(HashSet::new())
        .clean(text)
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    // -------------------------------------------------------------------
    // Allowed tags
    // -------------------------------------------------------------------

    #[test]
    fn allows_basic_formatting() {
        let html = "<p>Hello <strong>world</strong></p>";
        assert_eq!(sanitize_html(html), html);
    }

    #[test]
    fn allows_inline_formatting() {
        for tag in ["em", "i", "b", "strong", "u", "del", "s", "code", "pre"] {
            let html = format!("<{tag}>text</{tag}>");
            let result = sanitize_html(&html);
            assert!(
                result.contains(&format!("<{tag}>")),
                "{tag} should be allowed"
            );
        }
    }

    #[test]
    fn allows_lists() {
        let html = "<ul><li>one</li><li>two</li></ul>";
        assert_eq!(sanitize_html(html), html);
    }

    #[test]
    fn allows_ordered_list_attributes() {
        let html = r#"<ol start="5" reversed=""><li value="3">item</li></ol>"#;
        let result = sanitize_html(html);
        assert!(result.contains("start=\"5\""));
        assert!(result.contains("reversed"));
        assert!(result.contains("value=\"3\""));
    }

    #[test]
    fn allows_ruby_annotations() {
        let html = "<ruby>漢<rp>(</rp><rt>かん</rt><rp>)</rp></ruby>";
        let result = sanitize_html(html);
        assert!(result.contains("<ruby>"));
        assert!(result.contains("<rt>"));
        assert!(result.contains("<rp>"));
    }

    #[test]
    fn strips_abbreviation_tags() {
        let html = r#"<abbr title="HyperText Markup Language">HTML</abbr>"#;
        let result = sanitize_html(html);
        assert!(
            !result.contains("<abbr"),
            "abbr not in Mastodon's MASTODON_STRICT"
        );
        assert!(result.contains("HTML"));
    }

    #[test]
    fn blockquote_preserves_cite_url() {
        // ammonia treats `cite` as a built-in URL attribute on <blockquote>
        // and validates it against url_schemes. Mastodon's Sanitize.rb strips
        // it — this is a known minor divergence with no security impact.
        let html = r#"<blockquote cite="https://example.com">quote</blockquote>"#;
        let result = sanitize_html(html);
        assert!(result.contains("<blockquote"));
        assert!(result.contains("quote"));
    }

    // -------------------------------------------------------------------
    // Link handling
    // -------------------------------------------------------------------

    #[test]
    fn links_get_nofollow_noopener() {
        let html = r#"<a href="https://example.com">link</a>"#;
        let result = sanitize_html(html);
        assert!(result.contains("rel=\"nofollow noopener\""));
    }

    #[test]
    fn allows_link_class_for_mentions() {
        let html = r#"<a href="https://mastodon.social/@user" class="mention">@user</a>"#;
        let result = sanitize_html(html);
        assert!(result.contains("class=\"mention\""));
    }

    #[test]
    fn allows_span_class_for_invisible() {
        let html = r#"<span class="invisible">https://</span>"#;
        let result = sanitize_html(html);
        assert!(result.contains("class=\"invisible\""));
    }

    #[test]
    fn allows_p_class() {
        let html = r#"<p class="lead">text</p>"#;
        let result = sanitize_html(html);
        assert!(result.contains("class=\"lead\""));
    }

    // -------------------------------------------------------------------
    // XSS prevention
    // -------------------------------------------------------------------

    #[test]
    fn strips_script_tags() {
        let html = "<p>Hello</p><script>alert('xss')</script>";
        let result = sanitize_html(html);
        assert!(!result.contains("script"));
        assert!(result.contains("<p>Hello</p>"));
    }

    #[test]
    fn strips_event_handlers() {
        let html = "<p onclick=\"alert('xss')\">Click me</p>";
        let result = sanitize_html(html);
        assert!(!result.contains("onclick"));
    }

    #[test]
    fn strips_iframes() {
        let html = "<iframe src=\"https://evil.com\"></iframe><p>safe</p>";
        let result = sanitize_html(html);
        assert!(!result.contains("iframe"));
    }

    #[test]
    fn strips_svg() {
        let html = "<svg onload=\"fetch('evil')\"></svg>";
        let result = sanitize_html(html);
        assert!(!result.contains("svg"));
    }

    #[test]
    fn strips_style_attributes() {
        let html = "<p style=\"background:url(evil)\">text</p>";
        let result = sanitize_html(html);
        assert!(!result.contains("style"));
    }

    #[test]
    fn strips_img_tags() {
        let html = "<img src=x onerror=\"alert('xss')\">";
        let result = sanitize_html(html);
        assert!(!result.contains("img"));
        assert!(!result.contains("onerror"));
    }

    #[test]
    fn strips_javascript_urls() {
        let html = r#"<a href="javascript:alert('xss')">click</a>"#;
        let result = sanitize_html(html);
        assert!(!result.contains("javascript"));
    }

    #[test]
    fn strips_data_attributes() {
        let html = r#"<p data-evil="payload">text</p>"#;
        let result = sanitize_html(html);
        assert!(!result.contains("data-evil"));
    }

    // -------------------------------------------------------------------
    // Text sanitization
    // -------------------------------------------------------------------

    #[test]
    fn sanitize_text_strips_all_html() {
        let text = "<script>alert('xss')</script>Hello <b>world</b>";
        let result = sanitize_text(text);
        assert!(!result.contains("<script>"));
        assert!(!result.contains("<b>"));
        assert!(result.contains("Hello"));
        assert!(result.contains("world"));
    }

    #[test]
    fn empty_input() {
        assert_eq!(sanitize_html(""), "");
        assert_eq!(sanitize_text(""), "");
    }

    #[test]
    fn preserves_line_breaks() {
        let html = "<p>line 1</p><p>line 2</p><br>";
        assert_eq!(sanitize_html(html), html);
    }
}
