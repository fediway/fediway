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

// impl Embedding {
//     pub fn update(&mut self, embedding: &Embedding) {
//         if embedding.is_zero() {
//             return;
//         }

//         // let beta = (ALPHA * embedding.confidence)
//         //     .max(1.0 / ((self.updates as f64) + 1.0))
//         //     .max(DECAY);
//         // let decay = DECAY.min(beta);

//         // let alpha = 1.0;

//         // self.vec *= self.confidence.min(1.0);
//         // self.vec += &(embedding.vec.to_owned() * alpha * embedding.confidence);
//         // self.vec *= 1.0 / (self.confidence.min(1.0) + alpha * embedding.confidence + 0.00001);

//         // let beta = embedding.confidence / (embedding.confidence * 5.0);
//         // let k = 0.7;
//         // let lambda = 0.5;
//         // self.confidence += beta * (1.0 + embedding.confidence * k * (-lambda * self.confidence).exp());

//         // let decay = 0.2;
//         // self.vec *= 0.2;
//         // self.vec += &SparseVec::new(
//         //     embedding.vec.0.dim(),
//         //     embedding.vec.0.indices().iter().cloned().collect(),
//         //     embedding.vec.0.data().iter().map(|x| x.min(1.0)).collect()
//         // );

//         // let a_weight = self.confidence.max(0.1);
//         let a_weight = 0.1;
//         let b_weight = self.confidence.max(0.1);

//         self.vec *= a_weight;
//         self.vec += &(embedding.vec.to_owned() * b_weight);
//         self.vec *= 1.0 / (a_weight + b_weight);
//         // self.vec += &(embedding.vec.to_owned() * beta);
//         // self.vec.l1_normalize();
//         self.confidence +=
//             (1.0 - self.confidence) * (embedding.confidence / (embedding.confidence + 1.0));

//         // self.vec *= 1.0 - embedding.confidence;
//         // self.vec += &embedding.vec;
//         // // self.vec += &(embedding.vec.to_owned() * beta);
//         // self.vec.l1_normalize();
//         // self.confidence += (1.0 - self.confidence) * BETA * embedding.confidence;

//         self.updates += 1;
//         self.is_dirty = true;
//     }

//     pub fn is_zero(&self) -> bool {
//         self.vec.is_zero()
//     }
// }

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

    // fn get_weighted_statuses_tags_embedding(&self, status_id: &i64) -> Option<Embedding> {
    //     if let Some(tags) = self.statuses_tags.get(status_id) {
    //         self.get_weighted_tags_embedding(tags.value())
    //     } else {
    //         None
    //     }
    // }

    // fn get_weighted_tags_embedding(&self, tags: &[i64]) -> Option<Embedding> {
    //     let tag_embeddings: Vec<(SparseVec, f64)> = tags
    //         .iter()
    //         .filter_map(|t| match self.tags.get(t) {
    //             Some(e) => Some((e.vec.clone(), e.confidence)),
    //             _ => None,
    //         })
    //         .collect();

    //     if tag_embeddings.is_empty() {
    //         return None;
    //     }

    //     let mut vec: SparseVec = SparseVec::empty(self.communities.dim);

    //     let confidence_scores: Vec<f64> = tag_embeddings
    //         .iter()
    //         .map(|(_, confidence)| *confidence)
    //         .collect();
    //     let total_confidence: f64 = confidence_scores.iter().sum();
    //     let avg_confidence: f64 = total_confidence / (confidence_scores.len() as f64);

    //     for (c, (e, _)) in confidence_scores
    //         .into_iter()
    //         .zip(tag_embeddings.into_iter())
    //     {
    //         vec += &(e * (c / total_confidence));
    //     }

    //     Some(Embedding::new(vec, avg_confidence))
    // }

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

        // if let Some(tag) = self.get_weighted_tags_embedding(&tags) {
        //     status.update_embedding(tag.value(), event.created_at);
        // }

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
            // if let Some(t_embedding) = self.get_weighted_statuses_tags_embedding(&status_id) {
            //     consumer.update_embedding(&t_embedding, event_time);
            // }
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
