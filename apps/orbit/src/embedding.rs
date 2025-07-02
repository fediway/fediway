use serde::Deserialize;

use crate::communities::Communities;
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
    pub account_id: i64,
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
    pub communities: Communities,
    pub consumers: FastDashMap<i64, Consumer>,
    pub producers: FastDashMap<i64, Producer>,
    pub tags: FastDashMap<i64, Tag>,
    pub statuses: FastDashMap<i64, Status>,
    pub statuses_tags: FastDashMap<i64, Vec<i64>>,
}

pub struct Embedding {
    embedding: SparseVec
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
        communities: Communities,
        consumers: FastDashMap<i64, Consumer>,
        producers: FastDashMap<i64, Producer>,
        tags: FastDashMap<i64, Tag>,
    ) -> Self {
        Self {
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
        let tag_embeddings: Vec<(SparseVec, usize)> = tags
            .iter()
            .filter_map(|t| match self.tags.get(t) {
                Some(e) => Some((e.embedding().to_owned(), e.engagements)),
                _ => None,
            })
            .collect();

        if tag_embeddings.is_empty() {
            return None;
        }

        let mut weighted: SparseVec = SparseVec::empty(self.communities.dim);

        let total_engagements: f64 = tag_embeddings
            .iter()
            .map(|(_, e)| *e as f64)
            .sum();

        for (embedding, engagements) in tag_embeddings.into_iter()
        {
            weighted += &(embedding * (engagements as f64 / total_engagements));
        }

        Some(Embedding::new(weighted))
    }

    pub fn push_status(&self, event: StatusEvent) {
        // do nothing when status embedding already exists
        if self.statuses.contains_key(&event.status_id) {
            return;
        }

        let mut status = Status::empty(self.communities.dim, event.created_at);
        let tags: Vec<i64> = event.tags.unwrap_or_default().iter().cloned().collect();

        if let Some(producer) = self.producers.get(&event.account_id) {
            status.update_embedding(producer.value(), event.created_at);
        }

        if let Some(weighted_tags_embedding) = self.get_weighted_tags_embedding(&tags) {
            status.update_embedding(&weighted_tags_embedding, event.created_at);
        }

        self.statuses.insert(event.status_id, status);

        if !tags.is_empty() {
            self.statuses_tags.insert(event.status_id, tags);
        }
    }

    pub fn push_engagement(&self, event: EngagementEvent) {
        let account_id = event.account_id;
        let status_id = event.status_id;
        let author_id = event.author_id;
        let event_time = event.event_time;

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
            consumer.update_embedding(status.value(), event_time);

            // Add tag embedding if available
            if let Some(weighted_tags_embedding) = self.get_weighted_statuses_tags_embedding(&status_id) {
                consumer.update_embedding(&weighted_tags_embedding, event_time);
            }
        }

        // update status embedding
        if let Some(mut status) = self.statuses.get_mut(&status_id) {
            status.update_embedding(&old_consumer, event_time);
            status.engagements += 1;
        }

        // update producer embedding
        if let Some(mut producer) = self.producers.get_mut(&author_id) {
            producer.update_embedding(&old_consumer, event_time);
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
