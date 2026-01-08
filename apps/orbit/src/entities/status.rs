use std::time::SystemTime;

use crate::{
    embedding::{Embedded, UpdateEmbedding},
    entities::{Entity, Upsertable},
    sparse::SparseVec,
    utils::duration_since_or_zero,
};

const MIN_SPARSITY: usize = 5;
const MAX_SPARSITY: usize = 100;

const ALPHA: f64 = 0.00025;
const BETA: f64 = 1.0;
const GAMMA: f64 = 0.05;

pub struct Status {
    pub embedding: SparseVec,
    pub engagements: usize,
    pub created_at: SystemTime,
    last_upserted: Option<SystemTime>,
    is_dirty: bool,
}

impl Status {
    pub fn empty(dim: usize, created_at: SystemTime) -> Self {
        Self {
            embedding: SparseVec::empty(dim),
            engagements: 0,
            created_at,
            last_upserted: None,
            is_dirty: false,
        }
    }
}

impl Embedded for Status {
    fn embedding(&self) -> &SparseVec {
        &self.embedding
    }
}

impl<E: Embedded> UpdateEmbedding<E> for Status {
    fn update_embedding(&mut self, entity: &E, event_time: SystemTime) {
        if entity.embedding().is_zero() {
            return;
        }

        let time_since = match self.last_upserted {
            Some(t) => duration_since_or_zero(t, event_time),
            None => 0,
        } as f64;

        let decay = 1.0 - ((1.0 - (-ALPHA * time_since).exp()) * BETA);

        let mut normalized = entity.embedding().to_owned();
        normalized.normalize();

        self.embedding *= decay;
        self.embedding += &SparseVec::new(
            self.embedding.0.dim(),
            entity.embedding().0.indices().to_vec(),
            normalized
                .0
                .iter()
                .map(
                    |(community, value_other)| match self.embedding.0.get(community) {
                        Some(value) => (1.0 - value) * GAMMA * value_other,
                        None => GAMMA,
                    },
                )
                .collect(),
        );

        // self.embedding.keep_top_n(
        //     // (self.embedding.0.dim() / 10)
        //     //     .max(MAX_SPARSITY)
        //     //     .min(MIN_SPARSITY),
        //     15,
        // );
        self.last_upserted = Some(event_time);
        self.is_dirty = true;
    }
}

impl Entity for Status {
    fn is_dirty(&self) -> bool {
        self.is_dirty
    }

    fn is_dirty_mut(&mut self) -> &mut bool {
        &mut self.is_dirty
    }

    fn last_upserted(&self) -> &Option<SystemTime> {
        &self.last_upserted
    }

    fn last_upserted_mut(&mut self) -> &mut Option<SystemTime> {
        &mut self.last_upserted
    }

    fn should_upsert_entity(&self, config: &crate::config::Config) -> bool {
        // skip updating embeddings of statuses that have to few engagments
        if self.engagements < config.status_engagement_threshold {
            return false;
        }

        // // skip updating embeddings of statuses that are to old
        // let status_age = self.created_at.elapsed().unwrap().as_secs();
        // if status_age > config.max_status_age {
        //     return false;
        // }

        true
    }
}

impl Upsertable for Status {}
