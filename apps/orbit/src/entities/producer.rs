use std::time::SystemTime;

use crate::{
    embedding::{Embedded, FromEmbedding, UpdateEmbedding},
    entities::{Entity, Upsertable},
    sparse::SparseVec,
    utils::duration_since_or_zero,
};

const MIN_SPARSITY: usize = 5;
const MAX_SPARSITY: usize = 20;

// const BETA: f64 = 0.95;

const ALPHA: f64 = 0.0001;
const BETA: f64 = 1.0;
const GAMMA: f64 = 0.05;

pub struct Producer {
    embedding: SparseVec,
    last_upserted: Option<SystemTime>,
    pub engagements: usize,
    pub authority: f64,
    is_dirty: bool,
}

impl Embedded for Producer {
    fn embedding(&self) -> &SparseVec {
        &self.embedding
    }
}

impl<E: Embedded> UpdateEmbedding<E> for Producer {
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

        // self.embedding *= BETA;
        // self.embedding += &(entity.embedding().to_owned() * (1.0 - BETA));
        self.embedding.keep_top_n(
            // (self.embedding.0.dim() / 15)
            //     .max(MAX_SPARSITY)
            //     .min(MIN_SPARSITY),
            10,
        );

        // self.embedding.normalize();

        self.is_dirty = true;
    }
}

impl Entity for Producer {
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
        // skip updating embeddings of producers that have to few engagments
        if self.engagements < config.producer_engagement_threshold {
            return false;
        }

        true
    }
}

impl Upsertable for Producer {}

impl FromEmbedding for Producer {
    fn from_embedding(embedding: SparseVec) -> Self {
        Self {
            embedding,
            last_upserted: None,
            engagements: 0,
            authority: 0.0,
            is_dirty: false,
        }
    }
}
