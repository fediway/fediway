use std::time::SystemTime;

use crate::{
    embedding::{Embedded, FromEmbedding, UpdateEmbedding},
    entities::{Entity, Upsertable},
    sparse::SparseVec,
};

const MIN_SPARSITY: usize = 10;
const MAX_SPARSITY: usize = 50;
const BETA: f64 = 0.9;

#[derive(Clone)]
pub struct Consumer {
    embedding: SparseVec,
    last_upserted: Option<SystemTime>,
    is_dirty: bool,
}

impl Consumer {
    pub fn empty(dim: usize) -> Self {
        Self {
            embedding: SparseVec::empty(dim),
            last_upserted: None,
            is_dirty: false,
        }
    }
}

impl Embedded for Consumer {
    fn embedding(&self) -> &SparseVec {
        &self.embedding
    }
}

impl<E: Embedded> UpdateEmbedding<E> for Consumer {
    fn update_embedding(&mut self, entity: &E, _event_time: SystemTime) {
        if entity.embedding().is_zero() {
            return;
        }

        self.embedding *= BETA;
        self.embedding += &(entity.embedding().to_owned() * (1.0 - BETA));
        self.embedding.keep_top_n(
            (self.embedding.0.dim() / 10)
                .max(MAX_SPARSITY)
                .min(MIN_SPARSITY),
        );
        self.embedding.normalize();
        self.is_dirty = true;
    }
}

impl Entity for Consumer {
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

    fn should_upsert_entity(&self, _config: &crate::config::Config) -> bool {
        true // always upsert consumer
    }
}

impl Upsertable for Consumer {}

impl FromEmbedding for Consumer {
    fn from_embedding(embedding: SparseVec) -> Self {
        Self {
            embedding,
            last_upserted: None,
            is_dirty: false,
        }
    }
}
