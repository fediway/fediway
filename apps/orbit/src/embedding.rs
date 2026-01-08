use serde::Deserialize;

use crate::communities::Communities;
use crate::config::Config;
use crate::debezium::{DebeziumEvent, Operation, Payload};
use crate::entities::consumer::Consumer;
use crate::entities::producer::Producer;
use crate::entities::status::Status;
use crate::entities::tag::Tag;
use crate::sparse::SparseVec;
use crate::types::{FastDashMap, FastHashSet};
use crate::utils::deserialize_timestamp;
use std::time::SystemTime;

pub trait Embedded {
    fn embedding(&self) -> &SparseVec;
}

pub trait UpdateEmbedding<E: Embedded> {
    fn update_embedding(&mut self, entity: &E, event_time: SystemTime);
}

pub trait FromEmbedding {
    fn from_embedding(embedding: SparseVec) -> Self;
}

#[derive(Debug, Deserialize)]
pub struct StatusEvent {
    pub status_id: i64,
    pub author_id: i64,
    pub visibility: i32,
    pub sensitive: Option<bool>,
    pub tags: Option<FastHashSet<i64>>,
    #[serde(deserialize_with = "deserialize_timestamp")]
    pub created_at: SystemTime,
}

impl StatusEvent {
    pub fn age_in_seconds(&self) -> u64 {
        self.created_at.elapsed().unwrap_or_default().as_secs()
    }
}

#[derive(Debug, Deserialize)]
pub struct EngagementEvent {
    pub account_id: i64,
    pub status_id: i64,
    pub author_id: i64,
    #[serde(deserialize_with = "deserialize_timestamp")]
    pub event_time: SystemTime,
}

pub struct Embeddings {
    pub config: Config,
    pub communities: Communities,
    pub consumers: FastDashMap<i64, Consumer>,
    pub producers: FastDashMap<i64, Producer>,
    pub tags: FastDashMap<i64, Tag>,
    pub statuses: FastDashMap<i64, Status>,
    pub statuses_tags: FastDashMap<i64, Vec<i64>>,
}

pub struct Embedding {
    embedding: SparseVec,
}

impl Embedding {
    pub fn new(embedding: SparseVec) -> Self {
        Self { embedding }
    }
}

impl Embedded for Embedding {
    fn embedding(&self) -> &SparseVec {
        &self.embedding
    }
}

impl Embeddings {
    pub fn initial(
        config: Config,
        communities: Communities,
        consumers: FastDashMap<i64, Consumer>,
        producers: FastDashMap<i64, Producer>,
        tags: FastDashMap<i64, Tag>,
    ) -> Self {
        Self {
            config,
            communities,
            consumers,
            producers,
            tags,
            statuses: FastDashMap::default(),
            statuses_tags: FastDashMap::default(),
        }
    }

    fn get_weighted_statuses_tags_embedding(&self, status_id: &i64) -> Option<Embedding> {
        if let Some(tags) = self.statuses_tags.get(status_id) {
            self.get_weighted_tags_embedding(tags.value())
        } else {
            None
        }
    }

    fn get_weighted_tags_embedding(&self, tags: &[i64]) -> Option<Embedding> {
        let tag_embeddings: Vec<(SparseVec, Option<usize>, usize)> = tags
            .iter()
            .filter_map(|t| match self.tags.get(t) {
                Some(e) => Some((e.embedding().to_owned(), *e.community(), e.engagements)),
                _ => None,
            })
            .collect();

        if tag_embeddings.is_empty() {
            return None;
        }

        let mut weighted: SparseVec = SparseVec::empty(self.communities.dim);

        let total_engagements: f64 = tag_embeddings.iter().map(|(_, _, e)| *e as f64).sum();

        if total_engagements == 0.0 {
            return None;
        }

        let communities: FastHashSet<usize> =
            tag_embeddings.iter().filter_map(|(_, c, _)| *c).collect();

        for (embedding, _, engagements) in tag_embeddings.into_iter() {
            weighted += &(embedding * (engagements as f64 / total_engagements));
        }

        if communities.is_empty() {
            weighted.set_entries(communities.into_iter().collect(), 1.0);
        }

        Some(Embedding::new(weighted))
    }

    pub fn push_status(&self, event: DebeziumEvent<StatusEvent>) {
        if let Some(payload) = event.payload {
            match payload.op {
                Operation::Create => self.create_status(payload),
                Operation::Update => self.update_status(payload),
                Operation::Delete => self.delete_status(payload),
                _ => {}
            }
        }
    }

    fn create_status(&self, payload: Payload<StatusEvent>) {
        if let Some(event) = payload.after {
            // do nothing when status embedding already exists
            if self.statuses.contains_key(&event.status_id) {
                return;
            }

            let mut status = Status::empty(self.communities.dim, event.created_at);
            let tags: Vec<i64> = event.tags.unwrap_or_default().iter().cloned().collect();

            if let Some(producer) = self.producers.get(&event.author_id) {
                self.update_status_embedding(&mut status, producer.value(), event.created_at);
            }

            if let Some(weighted_tags_embedding) = self.get_weighted_tags_embedding(&tags) {
                self.update_status_embedding(
                    &mut status,
                    &weighted_tags_embedding,
                    event.created_at,
                );
            }

            self.statuses.insert(event.status_id, status);

            if !tags.is_empty() {
                self.statuses_tags.insert(event.status_id, tags);
            }
        }
    }

    fn update_status_embedding<E: Embedded>(
        &self,
        status: &mut Status,
        entity: &E,
        event_time: SystemTime,
    ) {
        status.update_embedding(entity, event_time);
        status.embedding.keep_top_n(self.config.status_sparsity * 2);
        // TODO: implement also for consumer, producer and tag
    }

    fn update_consumer_embedding<E: Embedded>(
        &self,
        consumer: &mut Consumer,
        entity: &E,
        event_time: SystemTime,
    ) {
        consumer.update_embedding(entity, event_time);
        consumer
            .embedding
            .keep_top_n(self.config.consumer_sparsity * 2);
        // TODO: implement also for consumer, producer and tag
    }

    fn update_producer_embedding<E: Embedded>(
        &self,
        producer: &mut Producer,
        entity: &E,
        event_time: SystemTime,
    ) {
        producer.update_embedding(entity, event_time);
        producer
            .embedding
            .keep_top_n(self.config.producer_sparsity * 2);
        // TODO: implement also for consumer, producer and tag
    }

    fn update_status(&self, payload: Payload<StatusEvent>) {
        // TODO: delete when changed to sensitive
    }

    fn delete_status(&self, payload: Payload<StatusEvent>) {
        if let Some(event) = payload.before {
            self.statuses.remove(&event.status_id);
            self.statuses_tags.remove(&event.status_id);
        }
    }

    pub fn push_engagement(&self, event: EngagementEvent) {
        let account_id = event.account_id;
        let status_id = event.status_id;
        let author_id = event.author_id;
        let event_time = event.event_time;

        if account_id == author_id {
            return;
        }

        let old_consumer = self
            .consumers
            .entry(account_id)
            .or_insert_with(|| Consumer::empty(self.communities.dim))
            .clone();

        // update consumer embedding
        if let (Some(mut consumer), Some(status)) = (
            self.consumers.get_mut(&account_id),
            self.statuses.get(&status_id),
        ) {
            self.update_consumer_embedding(&mut consumer, status.value(), event_time);
            // consumer.update_embedding(status.value(), event_time);

            // Add tag embedding if available
            if let Some(weighted_tags_embedding) =
                self.get_weighted_statuses_tags_embedding(&status_id)
            {
                self.update_consumer_embedding(&mut consumer, &weighted_tags_embedding, event_time);
                // consumer.update_embedding(&weighted_tags_embedding, event_time);
            }
        }

        // update status embedding
        if let Some(mut status) = self.statuses.get_mut(&status_id) {
            status.update_embedding(&old_consumer, event_time);
            status.engagements += 1;
        }

        // update producer embedding
        if let Some(mut producer) = self.producers.get_mut(&author_id) {
            self.update_producer_embedding(&mut producer, &old_consumer, event_time);
            producer.engagements += 1;
        }

        // update tag embeddings
        if let Some(tag_ids) = self.statuses_tags.get(&status_id) {
            for tag_id in tag_ids.value() {
                if let Some(mut tag) = self.tags.get_mut(tag_id) {
                    tag.update_embedding(&old_consumer, event_time);
                    tag.engagements += 1;
                }
            }
        }
    }
}
