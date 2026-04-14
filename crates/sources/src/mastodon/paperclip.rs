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
        is_local: bool,
    ) -> String {
        self.attachment_url("avatars", account_id, file_name, remote_url, is_local)
    }

    #[must_use]
    pub fn header_url(
        &self,
        account_id: i64,
        file_name: Option<&str>,
        remote_url: Option<&str>,
        is_local: bool,
    ) -> String {
        self.attachment_url("headers", account_id, file_name, remote_url, is_local)
    }

    fn attachment_url(
        &self,
        attachment: &str,
        account_id: i64,
        file_name: Option<&str>,
        remote_url: Option<&str>,
        is_local: bool,
    ) -> String {
        if let Some(name) = file_name {
            return self.build_file_url("accounts", attachment, account_id, name, is_local);
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
        is_local: bool,
    ) -> String {
        let partition = id_partition(id);
        if self.s3_enabled {
            let cache_prefix = if is_local { "" } else { "cache/" };
            format!(
                "https://{}/{cache_prefix}{class}/{attachment}/{partition}/original/{file_name}",
                self.host
            )
        } else {
            format!(
                "https://{}/system/{class}/{attachment}/{partition}/original/{file_name}",
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
        let url = local_config().avatar_url(42, Some("abc.jpg"), None, true);
        assert_eq!(
            url,
            "https://mastodon.example/system/accounts/avatars/000/000/042/original/abc.jpg"
        );
    }

    #[test]
    fn avatar_url_remote_account_local_mode_uses_local_path_when_cached() {
        let url = local_config().avatar_url(42, Some("abc.jpg"), None, false);
        assert_eq!(
            url,
            "https://mastodon.example/system/accounts/avatars/000/000/042/original/abc.jpg"
        );
    }

    #[test]
    fn avatar_url_local_account_s3_mode_no_cache_prefix() {
        let url = s3_config().avatar_url(42, Some("abc.jpg"), None, true);
        assert_eq!(
            url,
            "https://cdn.example/accounts/avatars/000/000/042/original/abc.jpg"
        );
    }

    #[test]
    fn avatar_url_remote_account_s3_mode_uses_cache_prefix() {
        let url = s3_config().avatar_url(42, Some("abc.jpg"), None, false);
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
            false,
        );
        assert_eq!(url, "https://other.example/avatars/abc.jpg");
    }

    #[test]
    fn avatar_url_falls_back_to_missing_when_no_data() {
        let url = local_config().avatar_url(42, None, None, true);
        assert_eq!(url, "https://mastodon.example/avatars/original/missing.png");
    }

    #[test]
    fn header_url_uses_headers_segment() {
        let url = local_config().header_url(42, Some("hdr.jpg"), None, true);
        assert_eq!(
            url,
            "https://mastodon.example/system/accounts/headers/000/000/042/original/hdr.jpg"
        );
    }

    #[test]
    fn header_url_falls_back_to_missing() {
        let url = local_config().header_url(42, None, None, true);
        assert_eq!(url, "https://mastodon.example/headers/original/missing.png");
    }
}
