#[derive(Clone)]
pub struct MediaConfig {
    pub host: String,
    pub s3_enabled: bool,
}

impl MediaConfig {
    #[must_use]
    pub fn new(host: String, s3_enabled: bool) -> Self {
        Self { host, s3_enabled }
    }

    #[must_use]
    pub fn avatar_url(
        &self,
        account_id: i64,
        file_name: Option<&str>,
        remote_url: Option<&str>,
        cached: bool,
    ) -> String {
        self.attachment_url("avatars", account_id, file_name, remote_url, cached)
    }

    #[must_use]
    pub fn header_url(
        &self,
        account_id: i64,
        file_name: Option<&str>,
        remote_url: Option<&str>,
        cached: bool,
    ) -> String {
        self.attachment_url("headers", account_id, file_name, remote_url, cached)
    }

    #[must_use]
    pub fn media_attachment_url(
        &self,
        media_id: i64,
        file_name: Option<&str>,
        remote_url: Option<&str>,
        cached: bool,
    ) -> Option<String> {
        if let Some(name) = file_name {
            return Some(self.build_file_url(
                "media_attachments",
                "files",
                media_id,
                name,
                cached,
                "original",
            ));
        }
        remote_url.map(ToString::to_string)
    }

    #[must_use]
    pub fn media_thumbnail_url(
        &self,
        media_id: i64,
        thumbnail_file_name: Option<&str>,
        cached: bool,
    ) -> Option<String> {
        thumbnail_file_name.map(|name| {
            self.build_file_url(
                "media_attachments",
                "files",
                media_id,
                name,
                cached,
                "small",
            )
        })
    }

    /// Mastodon prepends `cache/` to S3 URLs when an attachment's
    /// `{attachment}_storage_schema_version >= 1` AND its instance's `local?`
    /// returns false. `PreviewCard#local?` is hardcoded `false`, so for cards
    /// the version column is the sole discriminator. For other classes,
    /// `cached` is computed from both columns at the call site.
    /// See `mastodon/config/initializers/paperclip.rb` `:prefix_url`.
    #[must_use]
    pub fn preview_card_image_url(
        &self,
        card_id: i64,
        file_name: Option<&str>,
        cached: bool,
    ) -> Option<String> {
        file_name.map(|name| {
            self.build_file_url("preview_cards", "images", card_id, name, cached, "original")
        })
    }

    #[must_use]
    pub fn custom_emoji_url(
        &self,
        emoji_id: i64,
        file_name: Option<&str>,
        remote_url: Option<&str>,
        cached: bool,
    ) -> Option<String> {
        if let Some(name) = file_name {
            return Some(self.build_file_url(
                "custom_emojis",
                "images",
                emoji_id,
                name,
                cached,
                "original",
            ));
        }
        remote_url.map(ToString::to_string)
    }

    fn attachment_url(
        &self,
        attachment: &str,
        account_id: i64,
        file_name: Option<&str>,
        remote_url: Option<&str>,
        cached: bool,
    ) -> String {
        if let Some(name) = file_name {
            return self
                .build_file_url("accounts", attachment, account_id, name, cached, "original");
        }
        if let Some(remote) = remote_url {
            return remote.to_string();
        }
        format!("https://{}/{attachment}/original/missing.png", self.host)
    }

    fn build_file_url(
        &self,
        class: &str,
        attachment: &str,
        id: i64,
        file_name: &str,
        cached: bool,
        style: &str,
    ) -> String {
        let partition = id_partition(id);
        if self.s3_enabled {
            let cache_prefix = if cached { "cache/" } else { "" };
            format!(
                "https://{}/{cache_prefix}{class}/{attachment}/{partition}/{style}/{file_name}",
                self.host
            )
        } else {
            format!(
                "https://{}/system/{class}/{attachment}/{partition}/{style}/{file_name}",
                self.host
            )
        }
    }
}

#[must_use]
pub fn id_partition(id: i64) -> String {
    let s = format!("{id:09}");
    let take = s.len().min(18);
    s.as_bytes()[..take]
        .chunks(3)
        .map(|c| std::str::from_utf8(c).unwrap_or(""))
        .collect::<Vec<_>>()
        .join("/")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn local_config() -> MediaConfig {
        MediaConfig::new("mastodon.example".into(), false)
    }

    fn s3_config() -> MediaConfig {
        MediaConfig::new("cdn.example".into(), true)
    }

    #[test]
    fn id_partition_pads_short_id() {
        assert_eq!(id_partition(1), "000/000/001");
        assert_eq!(id_partition(12345), "000/012/345");
        assert_eq!(id_partition(999_999_999), "999/999/999");
    }

    #[test]
    fn id_partition_handles_snowflake_id() {
        assert_eq!(
            id_partition(114_782_619_229_607_682),
            "114/782/619/229/607/682"
        );
    }

    #[test]
    fn avatar_url_local_account_local_mode() {
        let url = local_config().avatar_url(42, Some("abc.jpg"), None, false);
        assert_eq!(
            url,
            "https://mastodon.example/system/accounts/avatars/000/000/042/original/abc.jpg"
        );
    }

    #[test]
    fn avatar_url_remote_account_local_mode_uses_local_path_when_cached() {
        let url = local_config().avatar_url(42, Some("abc.jpg"), None, true);
        assert_eq!(
            url,
            "https://mastodon.example/system/accounts/avatars/000/000/042/original/abc.jpg"
        );
    }

    #[test]
    fn avatar_url_local_account_s3_mode_no_cache_prefix() {
        let url = s3_config().avatar_url(42, Some("abc.jpg"), None, false);
        assert_eq!(
            url,
            "https://cdn.example/accounts/avatars/000/000/042/original/abc.jpg"
        );
    }

    #[test]
    fn avatar_url_remote_account_s3_mode_uses_cache_prefix() {
        let url = s3_config().avatar_url(42, Some("abc.jpg"), None, true);
        assert_eq!(
            url,
            "https://cdn.example/cache/accounts/avatars/000/000/042/original/abc.jpg"
        );
    }

    #[test]
    fn avatar_url_falls_back_to_remote_when_no_file() {
        let url = local_config().avatar_url(
            42,
            None,
            Some("https://other.example/avatars/abc.jpg"),
            true,
        );
        assert_eq!(url, "https://other.example/avatars/abc.jpg");
    }

    #[test]
    fn avatar_url_falls_back_to_missing_when_no_data() {
        let url = local_config().avatar_url(42, None, None, false);
        assert_eq!(url, "https://mastodon.example/avatars/original/missing.png");
    }

    #[test]
    fn header_url_uses_headers_segment() {
        let url = local_config().header_url(42, Some("hdr.jpg"), None, false);
        assert_eq!(
            url,
            "https://mastodon.example/system/accounts/headers/000/000/042/original/hdr.jpg"
        );
    }

    #[test]
    fn header_url_falls_back_to_missing() {
        let url = local_config().header_url(42, None, None, false);
        assert_eq!(url, "https://mastodon.example/headers/original/missing.png");
    }

    #[test]
    fn media_attachment_url_local_status_local_mode() {
        let url = local_config().media_attachment_url(7, Some("photo.jpg"), None, false);
        assert_eq!(
            url.as_deref(),
            Some(
                "https://mastodon.example/system/media_attachments/files/000/000/007/original/photo.jpg"
            )
        );
    }

    #[test]
    fn media_attachment_url_remote_status_s3_mode_uses_cache_prefix() {
        let url = s3_config().media_attachment_url(7, Some("photo.jpg"), None, true);
        assert_eq!(
            url.as_deref(),
            Some(
                "https://cdn.example/cache/media_attachments/files/000/000/007/original/photo.jpg"
            )
        );
    }

    #[test]
    fn media_attachment_url_falls_back_to_remote_when_no_file() {
        let url = local_config().media_attachment_url(
            7,
            None,
            Some("https://other.example/photo.jpg"),
            true,
        );
        assert_eq!(url.as_deref(), Some("https://other.example/photo.jpg"));
    }

    #[test]
    fn media_attachment_url_none_when_no_data() {
        let url = local_config().media_attachment_url(7, None, None, false);
        assert_eq!(url, None);
    }

    #[test]
    fn media_thumbnail_url_uses_small_style() {
        let url = local_config().media_thumbnail_url(7, Some("thumb.jpg"), false);
        assert_eq!(
            url.as_deref(),
            Some(
                "https://mastodon.example/system/media_attachments/files/000/000/007/small/thumb.jpg"
            )
        );
    }

    #[test]
    fn media_thumbnail_url_none_when_missing() {
        let url = local_config().media_thumbnail_url(7, None, false);
        assert_eq!(url, None);
    }

    #[test]
    fn preview_card_image_url_local_fs_has_no_cache_prefix() {
        let url = local_config().preview_card_image_url(99, Some("og.jpg"), true);
        assert_eq!(
            url.as_deref(),
            Some(
                "https://mastodon.example/system/preview_cards/images/000/000/099/original/og.jpg"
            )
        );
    }

    #[test]
    fn preview_card_image_url_s3_cached_adds_cache_prefix() {
        let url = s3_config().preview_card_image_url(99, Some("og.jpg"), true);
        assert_eq!(
            url.as_deref(),
            Some("https://cdn.example/cache/preview_cards/images/000/000/099/original/og.jpg")
        );
    }

    #[test]
    fn preview_card_image_url_s3_uncached_no_cache_prefix() {
        let url = s3_config().preview_card_image_url(99, Some("og.jpg"), false);
        assert_eq!(
            url.as_deref(),
            Some("https://cdn.example/preview_cards/images/000/000/099/original/og.jpg")
        );
    }

    #[test]
    fn preview_card_image_url_none_when_missing() {
        let url = local_config().preview_card_image_url(99, None, true);
        assert_eq!(url, None);
    }

    #[test]
    fn custom_emoji_url_local_emoji() {
        let url = local_config().custom_emoji_url(5, Some("party.png"), None, false);
        assert_eq!(
            url.as_deref(),
            Some(
                "https://mastodon.example/system/custom_emojis/images/000/000/005/original/party.png"
            )
        );
    }

    #[test]
    fn custom_emoji_url_federated_emoji_s3_mode_uses_cache_prefix() {
        let url = s3_config().custom_emoji_url(5, Some("party.png"), None, true);
        assert_eq!(
            url.as_deref(),
            Some("https://cdn.example/cache/custom_emojis/images/000/000/005/original/party.png")
        );
    }

    #[test]
    fn custom_emoji_url_falls_back_to_remote() {
        let url =
            local_config().custom_emoji_url(5, None, Some("https://other.example/emoji.png"), true);
        assert_eq!(url.as_deref(), Some("https://other.example/emoji.png"));
    }
}
