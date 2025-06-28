use crate::embedding::{EngagementEvent, StatusEvent};

pub struct KafkaWorker {}

impl KafkaWorker {}

pub enum Event {
    Status(StatusEvent),
    Engagement(EngagementEvent),
}
