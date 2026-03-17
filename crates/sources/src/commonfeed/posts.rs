use common::types::{Author, CardPreview, CustomEmoji, Engagement, Media, Post, Provider};
use feed::candidate::Candidate;
use feed::source::Source;

use super::types::{
    EmojiResult, LinkPreviewResult, MediaResult, PostResult, QueryFilters, QueryResponse,
};

pub struct PostsSource {
    algorithm: String,
    provider: Provider,
    filters: QueryFilters,
}

impl PostsSource {
    #[must_use]
    pub fn new(provider: Provider, algorithm: impl Into<String>) -> Self {
        Self {
            algorithm: algorithm.into(),
            provider,
            filters: QueryFilters::default(),
        }
    }

    #[must_use]
    pub fn with_filters(mut self, filters: QueryFilters) -> Self {
        self.filters = filters;
        self
    }
}

#[async_trait::async_trait]
impl Source<Post> for PostsSource {
    fn name(&self) -> &'static str {
        "commonfeed/posts"
    }

    async fn collect(&self, limit: usize) -> Vec<Candidate<Post>> {
        let response = super::fetch_json::<QueryResponse>(
            &self.provider,
            "posts",
            &self.algorithm,
            &self.filters,
            limit,
        )
        .await;

        match response {
            Some(r) => r.results.into_iter().map(into_candidate).collect(),
            None => Vec::new(),
        }
    }
}

fn into_candidate(result: PostResult) -> Candidate<Post> {
    let score = result.score.unwrap_or(0.0);
    let post = post_from_result(result);
    let mut candidate = Candidate::new(post, "commonfeed/posts");
    candidate.score = score;
    candidate
}

fn post_from_result(result: PostResult) -> Post {
    let engagement = result.engagement.as_ref();

    let media = result
        .media
        .unwrap_or_default()
        .into_iter()
        .filter_map(media_from_result)
        .collect();

    let quote = result.quote.map(|q| Box::new(post_from_result(*q)));
    let link = result.link.map(card_from_link_preview);

    Post {
        url: result.url,
        content: result.content,
        text: result.text,
        author: Author {
            handle: result.author.handle,
            display_name: result.author.name,
            url: result.author.url,
            avatar_url: result.author.avatar.map(|a| a.sizes.large.url),
            emojis: result
                .author
                .emojis
                .unwrap_or_default()
                .into_iter()
                .map(emoji_from_result)
                .collect(),
        },
        published_at: result.timestamp,
        language: result.language,
        sensitive: result.sensitive.unwrap_or(false),
        content_warning: result.content_warning,
        media,
        link,
        engagement: Engagement {
            replies: u64::from(
                engagement
                    .and_then(|e| e.replies)
                    .unwrap_or(0)
                    .max(0)
                    .cast_unsigned(),
            ),
            reposts: u64::from(
                engagement
                    .and_then(|e| e.reposts)
                    .unwrap_or(0)
                    .max(0)
                    .cast_unsigned(),
            ),
            likes: u64::from(
                engagement
                    .and_then(|e| e.likes)
                    .unwrap_or(0)
                    .max(0)
                    .cast_unsigned(),
            ),
        },
        reply_to: result.reply_to,
        quote,
        emojis: result
            .emojis
            .unwrap_or_default()
            .into_iter()
            .map(emoji_from_result)
            .collect(),
    }
}

fn emoji_from_result(e: EmojiResult) -> CustomEmoji {
    CustomEmoji {
        shortcode: e.shortcode,
        url: e.url.clone(),
        static_url: e.static_url.or(Some(e.url)),
    }
}

fn card_from_link_preview(link: LinkPreviewResult) -> CardPreview {
    let (image_url, image_width, image_height, blurhash) = link
        .image
        .map(|img| {
            (
                Some(img.sizes.large.url),
                img.sizes.large.width,
                img.sizes.large.height,
                img.blurhash,
            )
        })
        .unwrap_or_default();

    CardPreview {
        url: link.url,
        title: link.title,
        description: link.description,
        link_type: link.link_type,
        author_name: link.author_name,
        provider_name: link.provider_name,
        image_url,
        image_width,
        image_height,
        blurhash,
        embed_url: link.embed_url,
        embed_html: link.embed_html,
    }
}

/// Extract a [`Media`] from a `CommonFeed` [`MediaResult`].
///
/// Images carry their content in `image`, video/audio in `sizes`.
/// Returns `None` only when neither is present (malformed entry).
fn media_from_result(m: MediaResult) -> Option<Media> {
    let (url, mime_type, thumbnail_url, blurhash) = match (m.image, m.sizes, m.poster) {
        (Some(img), _, _) => (
            img.sizes.large.url,
            img.sizes.large.mime_type,
            img.sizes.small.map(|s| s.url),
            img.blurhash,
        ),
        (None, Some(sizes), poster) => {
            let (thumb, blur) = poster
                .map(|p| (Some(p.sizes.large.url), p.blurhash))
                .unwrap_or_default();
            (sizes.large.url, sizes.large.mime_type, thumb, blur)
        }
        _ => return None,
    };

    let (width, height) = m
        .original
        .map(|o| {
            (
                Some(o.width.max(0).cast_unsigned()),
                Some(o.height.max(0).cast_unsigned()),
            )
        })
        .unwrap_or_default();

    Some(Media {
        media_type: m.media_type,
        url,
        alt: m.alt,
        mime_type,
        width,
        height,
        blurhash,
        thumbnail_url,
    })
}

#[cfg(test)]
mod tests {
    use super::super::types::{
        AuthorResult, EngagementResult, ImageObject, MediaOriginal, SizeVariant, Sizes,
    };
    use super::*;

    fn bare_author() -> AuthorResult {
        AuthorResult {
            name: "Alice".into(),
            handle: "@alice@mastodon.social".into(),
            url: "https://mastodon.social/@alice".into(),
            avatar: None,
            emojis: None,
        }
    }

    fn image_object(url: &str) -> ImageObject {
        ImageObject {
            sizes: Sizes {
                small: None,
                medium: None,
                large: SizeVariant {
                    url: url.into(),
                    width: None,
                    height: None,
                    mime_type: Some("image/webp".into()),
                },
            },
            blurhash: None,
        }
    }

    #[test]
    fn converts_post_result_to_candidate() {
        let result = PostResult {
            url: "https://mastodon.social/@alice/123".into(),
            protocol: "activitypub".into(),
            content_type: "post".into(),
            content: "<p>hello</p>".into(),
            text: "hello".into(),
            author: bare_author(),
            timestamp: chrono::Utc::now(),
            language: Some("en".into()),
            sensitive: None,
            content_warning: None,
            media: None,
            engagement: Some(EngagementResult {
                likes: Some(42),
                reposts: Some(10),
                replies: Some(5),
            }),
            link: None,
            reply_to: None,
            quote: None,
            emojis: None,
            score: Some(0.85),
        };

        let candidate = into_candidate(result);
        assert_eq!(candidate.item.text, "hello");
        assert_eq!(candidate.item.author.display_name, "Alice");
        assert_eq!(candidate.item.engagement.likes, 42);
        assert_eq!(candidate.item.engagement.reposts, 10);
        assert_eq!(candidate.item.engagement.replies, 5);
        assert!((candidate.score - 0.85).abs() < f64::EPSILON);
        assert_eq!(candidate.source, "commonfeed/posts");
    }

    #[test]
    fn handles_missing_engagement() {
        let result = PostResult {
            url: "https://example.com/post/1".into(),
            protocol: "activitypub".into(),
            content_type: "post".into(),
            content: "<p>test</p>".into(),
            text: "test".into(),
            author: bare_author(),
            timestamp: chrono::Utc::now(),
            language: None,
            sensitive: None,
            content_warning: None,
            media: None,
            engagement: None,
            link: None,
            reply_to: None,
            quote: None,
            emojis: None,
            score: None,
        };

        let candidate = into_candidate(result);
        assert_eq!(candidate.item.engagement.likes, 0);
        assert_eq!(candidate.item.engagement.reposts, 0);
        assert_eq!(candidate.item.engagement.replies, 0);
        assert!(candidate.score.abs() < f64::EPSILON);
    }

    #[test]
    fn extracts_avatar_url_from_image_object() {
        let result = PostResult {
            url: "https://example.com/post/1".into(),
            protocol: "activitypub".into(),
            content_type: "post".into(),
            content: "".into(),
            text: "".into(),
            author: AuthorResult {
                name: "Bob".into(),
                handle: "@bob@example.com".into(),
                url: "https://example.com/@bob".into(),
                avatar: Some(image_object("https://cdn.example/avatar.webp")),
                emojis: None,
            },
            timestamp: chrono::Utc::now(),
            language: None,
            sensitive: None,
            content_warning: None,
            media: None,
            engagement: None,
            link: None,
            reply_to: None,
            quote: None,
            emojis: None,
            score: None,
        };

        let candidate = into_candidate(result);
        assert_eq!(
            candidate.item.author.avatar_url.as_deref(),
            Some("https://cdn.example/avatar.webp")
        );
    }

    #[test]
    fn extracts_image_media() {
        let media = media_from_result(MediaResult {
            media_type: "image".into(),
            alt: Some("A sunset".into()),
            image: Some(ImageObject {
                sizes: Sizes {
                    small: Some(SizeVariant {
                        url: "https://cdn.example/small.webp".into(),
                        width: Some(400),
                        height: Some(300),
                        mime_type: None,
                    }),
                    medium: None,
                    large: SizeVariant {
                        url: "https://cdn.example/large.webp".into(),
                        width: Some(1920),
                        height: Some(1080),
                        mime_type: Some("image/webp".into()),
                    },
                },
                blurhash: Some("LEHV6nWB2yk8".into()),
            }),
            original: Some(MediaOriginal {
                width: 3840,
                height: 2160,
            }),
            sizes: None,
            poster: None,
        })
        .unwrap();

        assert_eq!(media.media_type, "image");
        assert_eq!(media.url, "https://cdn.example/large.webp");
        assert_eq!(media.alt.as_deref(), Some("A sunset"));
        assert_eq!(media.mime_type.as_deref(), Some("image/webp"));
        assert_eq!(media.width, Some(3840));
        assert_eq!(media.height, Some(2160));
        assert_eq!(media.blurhash.as_deref(), Some("LEHV6nWB2yk8"));
        assert_eq!(
            media.thumbnail_url.as_deref(),
            Some("https://cdn.example/small.webp")
        );
    }

    #[test]
    fn extracts_video_media() {
        let media = media_from_result(MediaResult {
            media_type: "video".into(),
            alt: None,
            image: None,
            original: Some(MediaOriginal {
                width: 1920,
                height: 1080,
            }),
            sizes: Some(Sizes {
                small: None,
                medium: None,
                large: SizeVariant {
                    url: "https://cdn.example/video.mp4".into(),
                    width: None,
                    height: None,
                    mime_type: Some("video/mp4".into()),
                },
            }),
            poster: Some(ImageObject {
                sizes: Sizes {
                    small: None,
                    medium: None,
                    large: SizeVariant {
                        url: "https://cdn.example/poster.webp".into(),
                        width: Some(1280),
                        height: Some(720),
                        mime_type: None,
                    },
                },
                blurhash: Some("L6PZfSi_.AyE".into()),
            }),
        })
        .unwrap();

        assert_eq!(media.media_type, "video");
        assert_eq!(media.url, "https://cdn.example/video.mp4");
        assert_eq!(media.mime_type.as_deref(), Some("video/mp4"));
        assert_eq!(media.width, Some(1920));
        assert_eq!(media.height, Some(1080));
        assert_eq!(media.blurhash.as_deref(), Some("L6PZfSi_.AyE"));
        assert_eq!(
            media.thumbnail_url.as_deref(),
            Some("https://cdn.example/poster.webp")
        );
    }

    #[test]
    fn drops_media_without_content() {
        let result = media_from_result(MediaResult {
            media_type: "image".into(),
            alt: None,
            image: None,
            original: None,
            sizes: None,
            poster: None,
        });
        assert!(result.is_none());
    }
}
