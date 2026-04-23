use common::paperclip::MediaConfig;

#[must_use]
pub fn test_media() -> MediaConfig {
    MediaConfig::new("local.test".into(), false)
}

#[must_use]
pub fn test_media_s3() -> MediaConfig {
    MediaConfig::new("files.test".into(), true)
}
