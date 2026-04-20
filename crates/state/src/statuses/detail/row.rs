use std::collections::{HashMap, HashSet};

use chrono::{DateTime, NaiveDateTime, Utc};
use common::ids::StatusId;
use common::paperclip::MediaConfig;
use mastodon::formatter;
use mastodon::sanitize::{sanitize_html, sanitize_text};
use mastodon::{
    Account, CustomEmoji, Field, MediaAttachment, MediaMeta, MediaMetaDimensions, Mention,
    PreviewCard, PreviewCardAuthor, QuoteApproval, Status, Tag,
};
use regex::Regex;
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use sqlx::types::Json;

#[derive(FromRow)]
pub(super) struct BaseRow {
    pub(super) id: StatusId,
    pub(super) account_id: i64,
    pub(super) uri: Option<String>,
    pub(super) url: Option<String>,
    pub(super) text: String,
    pub(super) spoiler_text: String,
    pub(super) sensitive: bool,
    pub(super) language: Option<String>,
    pub(super) in_reply_to_id: Option<StatusId>,
    pub(super) in_reply_to_account_id: Option<i64>,
    pub(super) created_at: NaiveDateTime,
    pub(super) edited_at: Option<NaiveDateTime>,
    pub(super) username: String,
    pub(super) domain: Option<String>,
    pub(super) display_name: String,
    pub(super) note: String,
    pub(super) account_url: Option<String>,
    pub(super) account_uri: String,
    pub(super) avatar_file_name: Option<String>,
    pub(super) avatar_remote_url: Option<String>,
    pub(super) header_file_name: Option<String>,
    pub(super) header_remote_url: String,
    pub(super) account_created_at: NaiveDateTime,
    pub(super) discoverable: Option<bool>,
    pub(super) indexable: bool,
    pub(super) locked: bool,
    pub(super) actor_type: Option<String>,
    pub(super) fields: Option<Json<Vec<FieldRow>>>,
    pub(super) statuses_count: i64,
    pub(super) following_count: i64,
    pub(super) followers_count: i64,
    pub(super) last_status_at: Option<NaiveDateTime>,
}

#[derive(Default, Clone)]
pub(super) struct StatsRow {
    pub(super) replies: i64,
    pub(super) reblogs: i64,
    pub(super) favourites: i64,
    pub(super) quotes: i64,
}

#[derive(FromRow)]
pub(super) struct StatsTuple {
    pub(super) status_id: StatusId,
    pub(super) replies_count: i64,
    pub(super) reblogs_count: i64,
    pub(super) favourites_count: i64,
    pub(super) quotes_count: i64,
}

#[derive(FromRow)]
pub(super) struct MediaRow {
    pub(super) id: i64,
    pub(super) status_id: StatusId,
    pub(super) media_type: MediaKind,
    pub(super) description: Option<String>,
    pub(super) remote_url: String,
    pub(super) blurhash: Option<String>,
    pub(super) file_file_name: Option<String>,
    pub(super) file_meta: Option<serde_json::Value>,
    pub(super) thumbnail_file_name: Option<String>,
    pub(super) account_is_local: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, sqlx::Type)]
#[repr(i32)]
pub(super) enum MediaKind {
    Image = 0,
    Gifv = 1,
    Video = 2,
    Unknown = 3,
    Audio = 4,
}

impl MediaKind {
    fn as_api_str(self) -> &'static str {
        match self {
            Self::Image => "image",
            Self::Gifv => "gifv",
            Self::Video => "video",
            Self::Audio => "audio",
            Self::Unknown => "unknown",
        }
    }
}

#[derive(FromRow)]
pub(super) struct CardRow {
    pub(super) status_id: StatusId,
    pub(super) id: i64,
    pub(super) url: String,
    pub(super) title: String,
    pub(super) description: String,
    pub(super) card_type: CardKind,
    pub(super) html: String,
    pub(super) author_name: String,
    pub(super) author_url: String,
    pub(super) provider_name: String,
    pub(super) provider_url: String,
    pub(super) image_file_name: Option<String>,
    pub(super) image_description: String,
    pub(super) width: i32,
    pub(super) height: i32,
    pub(super) embed_url: String,
    pub(super) blurhash: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, sqlx::Type)]
#[repr(i32)]
pub(super) enum CardKind {
    Link = 0,
    Photo = 1,
    Video = 2,
    Rich = 3,
}

impl CardKind {
    fn as_api_str(self) -> &'static str {
        match self {
            Self::Link => "link",
            Self::Photo => "photo",
            Self::Video => "video",
            Self::Rich => "rich",
        }
    }
}

#[derive(FromRow)]
pub(super) struct MentionRow {
    pub(super) status_id: StatusId,
    pub(super) account_id: i64,
    pub(super) username: String,
    pub(super) domain: Option<String>,
    pub(super) url: Option<String>,
}

#[derive(FromRow)]
pub(super) struct EmojiRow {
    pub(super) id: i64,
    pub(super) shortcode: String,
    pub(super) domain: Option<String>,
    pub(super) image_file_name: Option<String>,
    pub(super) image_remote_url: Option<String>,
}

#[derive(Deserialize, Serialize)]
pub(super) struct FieldRow {
    #[serde(default)]
    pub(super) name: String,
    #[serde(default)]
    pub(super) value: String,
    #[serde(default)]
    pub(super) verified_at: Option<DateTime<Utc>>,
}

#[derive(Default)]
pub(super) struct ViewerState {
    pub(super) favourited: HashSet<StatusId>,
    pub(super) bookmarked: HashSet<StatusId>,
    pub(super) reblogged: HashSet<StatusId>,
}

pub(super) struct Enrichment<'a> {
    pub(super) stats: &'a HashMap<StatusId, StatsRow>,
    pub(super) media: &'a HashMap<StatusId, Vec<MediaRow>>,
    pub(super) tags: &'a HashMap<StatusId, Vec<String>>,
    pub(super) cards: &'a HashMap<StatusId, CardRow>,
    pub(super) mentions: &'a HashMap<StatusId, Vec<MentionRow>>,
    pub(super) emojis: &'a HashMap<String, EmojiRow>,
    pub(super) viewer: &'a ViewerState,
}

pub(super) fn build_status(
    row: BaseRow,
    instance_domain: &str,
    media: &MediaConfig,
    enrich: &Enrichment<'_>,
) -> Status {
    let status_id = row.id;
    let stat = enrich.stats.get(&status_id).cloned().unwrap_or_default();

    let account = build_account(&row, instance_domain, media, enrich.emojis);

    let media_attachments = enrich
        .media
        .get(&status_id)
        .map(|rows| {
            rows.iter()
                .map(|m| build_media_attachment(m, media))
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let tag_list = enrich
        .tags
        .get(&status_id)
        .map(|names| {
            names
                .iter()
                .map(|name| Tag {
                    name: name.clone(),
                    url: format!("https://{instance_domain}/tags/{name}"),
                    history: Vec::new(),
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let mention_list = enrich
        .mentions
        .get(&status_id)
        .map(|rows| {
            rows.iter()
                .map(|m| build_mention(m, instance_domain))
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let content_emojis = build_emojis(
        &[row.text.as_str(), row.spoiler_text.as_str()],
        enrich.emojis,
        media,
    );

    let card = enrich.cards.get(&status_id).map(|c| build_card(c, media));

    let published_at = row.created_at.and_utc();
    let spoiler = sanitize_text(&row.spoiler_text);
    let fallback_url = format!("https://{instance_domain}/@{}/{}", row.username, row.id.0);
    let url = row
        .url
        .clone()
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| fallback_url.clone());
    let uri = row
        .uri
        .clone()
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| url.clone());

    let content = if row.domain.is_none() {
        formatter::format_local(&row.text, &mention_list, &tag_list, instance_domain)
    } else {
        formatter::format_remote(&row.text)
    };

    Status {
        id: status_id.0.to_string(),
        uri,
        url: Some(url),
        created_at: published_at,
        edited_at: row.edited_at.map(|dt| dt.and_utc()),
        content,
        text: Some(row.text),
        visibility: "public",
        language: row.language,
        sensitive: row.sensitive,
        spoiler_text: spoiler,
        in_reply_to_id: row.in_reply_to_id.map(|i| i.0.to_string()),
        in_reply_to_account_id: row.in_reply_to_account_id.map(|i| i.to_string()),
        account,
        media_attachments,
        mentions: mention_list,
        tags: tag_list,
        emojis: content_emojis,
        reblog: None,
        reblogs_count: u64::try_from(stat.reblogs).unwrap_or(0),
        favourites_count: u64::try_from(stat.favourites).unwrap_or(0),
        replies_count: u64::try_from(stat.replies).unwrap_or(0),
        quotes_count: u64::try_from(stat.quotes).unwrap_or(0),
        favourited: enrich.viewer.favourited.contains(&status_id),
        reblogged: enrich.viewer.reblogged.contains(&status_id),
        muted: false,
        bookmarked: enrich.viewer.bookmarked.contains(&status_id),
        pinned: false,
        quote: None,
        quote_approval: QuoteApproval::public(),
        poll: None,
        filtered: Vec::new(),
        card,
    }
}

pub(super) fn build_account(
    row: &BaseRow,
    instance_domain: &str,
    media: &MediaConfig,
    emojis: &HashMap<String, EmojiRow>,
) -> Account {
    let is_local = row.domain.is_none();
    let acct = match &row.domain {
        Some(d) => format!("{}@{}", row.username, d),
        None => row.username.clone(),
    };
    let url = row
        .account_url
        .clone()
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| format!("https://{instance_domain}/@{acct}"));
    let uri = if row.account_uri.is_empty() {
        format!("https://{instance_domain}/users/{}", row.username)
    } else {
        row.account_uri.clone()
    };

    let avatar = media.avatar_url(
        row.account_id,
        row.avatar_file_name.as_deref(),
        row.avatar_remote_url.as_deref(),
        is_local,
    );
    let header = media.header_url(
        row.account_id,
        row.header_file_name.as_deref(),
        non_empty(&row.header_remote_url),
        is_local,
    );

    let bot = matches!(row.actor_type.as_deref(), Some("Service" | "Application"));
    let group = row.actor_type.as_deref() == Some("Group");

    let fields = row
        .fields
        .as_ref()
        .map(|rows| {
            rows.0
                .iter()
                .map(|f| Field {
                    name: sanitize_text(&f.name),
                    value: sanitize_html(&f.value),
                    verified_at: f.verified_at,
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let account_emojis = build_emojis(
        &[row.display_name.as_str(), row.note.as_str()],
        emojis,
        media,
    );

    Account {
        id: row.account_id.to_string(),
        username: row.username.clone(),
        acct,
        url,
        uri,
        display_name: sanitize_text(&row.display_name),
        note: sanitize_html(&row.note),
        avatar: avatar.clone(),
        avatar_static: avatar,
        header: header.clone(),
        header_static: header,
        locked: row.locked,
        bot,
        group,
        discoverable: row.discoverable,
        indexable: row.indexable,
        statuses_count: u64::try_from(row.statuses_count).unwrap_or(0),
        followers_count: u64::try_from(row.followers_count).unwrap_or(0),
        following_count: u64::try_from(row.following_count).unwrap_or(0),
        created_at: row.account_created_at.and_utc(),
        fields,
        emojis: account_emojis,
        last_status_at: row
            .last_status_at
            .map(|dt| dt.date().format("%Y-%m-%d").to_string()),
    }
}

pub(super) fn build_media_attachment(row: &MediaRow, media: &MediaConfig) -> MediaAttachment {
    let url = media.media_attachment_url(
        row.id,
        row.file_file_name.as_deref(),
        non_empty(&row.remote_url),
        row.account_is_local,
    );
    let preview_url = media
        .media_thumbnail_url(
            row.id,
            row.thumbnail_file_name.as_deref(),
            row.account_is_local,
        )
        .or_else(|| url.clone());
    let (width, height) = file_meta_dimensions(row.file_meta.as_ref());
    let meta = match (width, height) {
        (Some(w), Some(h)) if w > 0 && h > 0 => Some(MediaMeta {
            original: Some(MediaMetaDimensions::new(w, h)),
            small: None,
        }),
        _ => None,
    };

    MediaAttachment {
        id: row.id.to_string(),
        media_type: row.media_type.as_api_str().to_owned(),
        url,
        preview_url,
        remote_url: non_empty(&row.remote_url).map(str::to_owned),
        meta,
        description: row.description.as_deref().map(sanitize_text),
        blurhash: row.blurhash.clone(),
    }
}

pub(super) fn build_card(row: &CardRow, media: &MediaConfig) -> PreviewCard {
    let image = media.preview_card_image_url(row.id, row.image_file_name.as_deref());
    PreviewCard {
        url: row.url.clone(),
        title: sanitize_text(&row.title),
        description: sanitize_text(&row.description),
        card_type: row.card_type.as_api_str().to_owned(),
        authors: if row.author_name.is_empty() {
            Vec::new()
        } else {
            vec![PreviewCardAuthor {
                name: row.author_name.clone(),
                url: row.author_url.clone(),
                account: None,
            }]
        },
        author_name: sanitize_text(&row.author_name),
        author_url: row.author_url.clone(),
        provider_name: sanitize_text(&row.provider_name),
        provider_url: row.provider_url.clone(),
        html: sanitize_html(&row.html),
        width: row.width,
        height: row.height,
        image,
        image_description: sanitize_text(&row.image_description),
        embed_url: non_empty(&row.embed_url).map(str::to_owned),
        blurhash: row.blurhash.clone(),
        history: Vec::new(),
    }
}

pub(super) fn build_mention(row: &MentionRow, instance_domain: &str) -> Mention {
    let acct = match &row.domain {
        Some(d) => format!("{}@{}", row.username, d),
        None => row.username.clone(),
    };
    let url = row
        .url
        .clone()
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| format!("https://{instance_domain}/@{acct}"));
    Mention {
        id: row.account_id.to_string(),
        username: row.username.clone(),
        url,
        acct,
    }
}

pub(super) fn build_emojis(
    texts: &[&str],
    emojis: &HashMap<String, EmojiRow>,
    media: &MediaConfig,
) -> Vec<CustomEmoji> {
    let mut used: HashSet<String> = HashSet::new();
    let mut out: Vec<CustomEmoji> = Vec::new();
    for text in texts {
        for m in shortcode_regex().captures_iter(text) {
            let Some(shortcode) = m.get(1).map(|c| c.as_str()) else {
                continue;
            };
            if used.contains(shortcode) {
                continue;
            }
            let Some(emoji) = emojis.get(shortcode) else {
                continue;
            };
            let is_local = emoji.domain.is_none();
            let Some(url) = media.custom_emoji_url(
                emoji.id,
                emoji.image_file_name.as_deref(),
                emoji.image_remote_url.as_deref(),
                is_local,
            ) else {
                continue;
            };
            out.push(CustomEmoji {
                shortcode: emoji.shortcode.clone(),
                static_url: url.clone(),
                url,
                visible_in_picker: true,
            });
            used.insert(shortcode.to_owned());
        }
    }
    out
}

pub(super) fn scan_shortcodes(base: &[BaseRow]) -> HashSet<String> {
    let re = shortcode_regex();
    let mut set = HashSet::new();
    for row in base {
        for text in [
            row.text.as_str(),
            row.spoiler_text.as_str(),
            row.display_name.as_str(),
            row.note.as_str(),
        ] {
            for m in re.captures_iter(text) {
                if let Some(c) = m.get(1) {
                    set.insert(c.as_str().to_owned());
                }
            }
        }
    }
    set
}

fn shortcode_regex() -> &'static Regex {
    use std::sync::OnceLock;
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r":([a-zA-Z0-9_]{2,}):").expect("valid regex"))
}

fn non_empty(s: &str) -> Option<&str> {
    if s.is_empty() { None } else { Some(s) }
}

fn file_meta_dimensions(meta: Option<&serde_json::Value>) -> (Option<u32>, Option<u32>) {
    let Some(meta) = meta else {
        return (None, None);
    };
    let original = meta.get("original");
    let width = original
        .and_then(|v| v.get("width"))
        .and_then(serde_json::Value::as_u64)
        .and_then(|n| u32::try_from(n).ok());
    let height = original
        .and_then(|v| v.get("height"))
        .and_then(serde_json::Value::as_u64)
        .and_then(|n| u32::try_from(n).ok());
    (width, height)
}
