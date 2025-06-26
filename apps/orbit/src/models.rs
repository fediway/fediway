use std::collections::HashSet;
use std::time::SystemTime;

pub struct Status {
    pub status_id: i64,
    pub account_id: i64,
    pub tags: HashSet<i64>,
    pub created_at: SystemTime,
}

pub struct Engagement {
    pub account_id: i64,
    pub status_id: i64,
    pub author_id: i64,
    pub event_time: SystemTime,
}
