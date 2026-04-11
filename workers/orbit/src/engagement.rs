use chrono::NaiveDateTime;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EngagementKind {
    Like,
    Repost,
    Reply,
    Bookmark,
}

impl EngagementKind {
    #[must_use]
    pub fn weight(self) -> f32 {
        match self {
            Self::Like => 1.0,
            Self::Repost => 1.5,
            Self::Reply => 3.0,
            Self::Bookmark => 2.0,
        }
    }

    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Like => "favourites",
            Self::Repost => "reblogs",
            Self::Reply => "replies",
            Self::Bookmark => "bookmarks",
        }
    }
}

#[derive(Debug)]
pub struct RawEngagement {
    pub id: i64,
    pub account_id: i64,
    pub created_at: NaiveDateTime,
    pub kind: EngagementKind,
    pub target: TargetPost,
}

#[derive(Debug)]
pub struct TargetPost {
    pub text: String,
    pub spoiler_text: String,
    pub author_name: String,
    pub author_handle: String,
    pub alt_texts: Vec<String>,
    pub tags: Vec<String>,
}
