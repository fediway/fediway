use std::time::SystemTime;

use crate::{
    embedding::{Embedded, FromEmbedding, UpdateEmbedding},
    entities::{Entity, Upsertable},
    sparse::SparseVec,
};

const MIN_SPARSITY: usize = 10;
const MAX_SPARSITY: usize = 25;

const BETA: f64 = 0.95;

pub struct Tag {
    embedding: SparseVec,
    pub engagements: usize,
    last_upserted: Option<SystemTime>,
    is_dirty: bool,
}

impl Embedded for Tag {
    fn embedding(&self) -> &SparseVec {
        &self.embedding
    }
}

impl<E: Embedded> UpdateEmbedding<E> for Tag {
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

impl FromEmbedding for Tag {
    fn from_embedding(embedding: SparseVec) -> Self {
        Self {
            embedding,
            engagements: 0,
            last_upserted: None,
            is_dirty: false,
        }
    }
}

impl Entity for Tag {
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
        // skip updating embeddings of tags that have to few engagments
        if self.engagements < config.tag_engagement_threshold {
            return false;
        }

        true
    }
}

impl Upsertable for Tag {}
