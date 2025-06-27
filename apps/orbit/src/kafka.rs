use crate::types::FastHashSet;
use std::time::SystemTime;

pub struct KafkaWorker {}

impl KafkaWorker {}

pub enum Event {
    Status(StatusEvent),
    Engagement(EngagementEvent),
}

#[derive(Debug)]
pub struct StatusEvent {
    pub status_id: i64,
    pub account_id: i64,
    pub tags: FastHashSet<i64>,
    pub created_at: SystemTime,
}

#[derive(Debug)]
pub struct EngagementEvent {
    pub account_id: i64,
    pub status_id: i64,
    pub author_id: i64,
    pub event_time: SystemTime,
}
