use serde::Serialize;

use crate::status::Status;

/// Mastodon-compatible Quote entity.
/// See: <https://docs.joinmastodon.org/entities/Quote/>
#[derive(Debug, Serialize)]
pub struct Quote {
    pub state: &'static str,
    pub quoted_status: Box<Status>,
}

/// Mastodon-compatible `QuoteApproval` entity.
/// See: <https://docs.joinmastodon.org/entities/QuoteApproval/>
#[derive(Debug, Serialize)]
pub struct QuoteApproval {
    pub automatic: Vec<&'static str>,
    pub manual: Vec<&'static str>,
    pub current_user: &'static str,
}

impl QuoteApproval {
    /// Default approval for public posts: anyone can quote automatically.
    #[must_use]
    pub fn public() -> Self {
        Self {
            automatic: vec!["public"],
            manual: Vec::new(),
            current_user: "automatic",
        }
    }
}
