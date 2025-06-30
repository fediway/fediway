use std::time::{Duration, SystemTime};

use crate::{config::Config, embedding::Embedded};

pub mod consumer;
pub mod producer;
pub mod status;
pub mod tag;

pub enum EntityType {
    Consumer,
    Producer,
    Status,
    Tag,
}

pub trait Entity {
    fn is_dirty(&self) -> bool;
    fn is_dirty_mut(&mut self) -> &mut bool;

    fn last_upserted(&self) -> &Option<SystemTime>;
    fn last_upserted_mut(&mut self) -> &mut Option<SystemTime>;

    fn should_upsert_entity(&self, config: &Config) -> bool;
}

pub trait Upsertable: Embedded + Entity {
    fn should_upsert(&self, config: &Config) -> bool {
        // skip updating embeddings that:
        // - have not been changed since last udpate
        // - are zero
        if !self.is_dirty() || self.embedding().is_zero() {
            return false;
        }

        // skip updating embeddings that have been updated recently
        if let Some(last_upserted) = self.last_upserted() {
            let now = SystemTime::now();
            let update_delay = Duration::from_secs(config.qdrant_upsert_delay);

            if *last_upserted > now - update_delay {
                println!("recently upserted");
                return false;
            }
        }

        self.should_upsert_entity(config)
    }
}
