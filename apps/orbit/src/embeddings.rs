use std::collections::{HashMap};

use crate::algo::weighted_louvain::Communities;
use crate::models::{Engagement, Status};
use crate::sparse::SparseVec;

const LAMBDA: f64 = 0.05;
const ALPHA: f64 = 0.01;
const BETA: f64 = 0.1;

pub struct Embedding {
    pub vec: SparseVec,
    pub confidence: f64,
    updates: usize,
}

impl Embedding {
    pub fn empty(dim: usize) -> Self {
        Self {
            vec: SparseVec::empty(dim),
            confidence: 0.0,
            updates: 0,
        }
    }

    pub fn new(vec: SparseVec, confidence: f64) -> Self {
        Self {
            vec,
            confidence,
            updates: 0,
        }
    }

    pub fn update(&mut self, embedding: &Embedding) {
        let beta = (ALPHA * embedding.confidence).max(1.0 / ((self.updates as f64) + 1.0));
        // self.vec *= 1.0 - beta;
        self.vec += &(embedding.vec.to_owned() * beta);
        self.vec.l1_normalize();
        self.updates += 1;
        self.confidence += (1.0 - self.confidence) * BETA * embedding.confidence;

        if self.updates % 2 == 0 {
            self.vec.keep_top_n(20);
        }
    }

    pub fn is_zero(&self) -> bool {
        self.vec.is_zero()
    }
}

pub struct Embeddings {
    communities: Communities,
    pub consumers: HashMap<i64, Embedding>,
    producers: HashMap<i64, Embedding>,
    tags: HashMap<i64, Embedding>,
    statuses: HashMap<i64, Embedding>,
    statuses_tags: HashMap<i64, Vec<i64>>,
    dim: usize,
}

impl Embeddings {
    pub fn initial(
        communities: Communities,
        consumers: HashMap<i64, Embedding>,
        producers: HashMap<i64, Embedding>,
        tags: HashMap<i64, Embedding>,
    ) -> Self {
        Self {
            dim: communities.0.values().max().unwrap() + 1,
            communities,
            consumers,
            producers,
            tags,
            statuses: HashMap::new(),
            statuses_tags: HashMap::new(),
        }
    }

    fn get_weighted_statuses_tags_embedding(&self, status_id: &i64) -> Option<Embedding> {
        if let Some(tags) = self.statuses_tags.get(status_id) {
            self.get_weighted_tags_embedding(tags)
        } else {
            None
        }
    }

    fn get_statuses_tags(&self, status_id: &i64) -> Vec<i64> {
        if let Some(tags) = self.statuses_tags.get(status_id) {
            tags.clone()
        } else {
            Vec::new()
        }
    }

    fn get_weighted_tags_embedding(&self, tags: &[i64]) -> Option<Embedding> {
        let tag_embeddings: Vec<&Embedding> =
            tags.iter().filter_map(|t| self.tags.get(t)).collect();

        if tag_embeddings.is_empty() {
            return None;
        }

        let mut vec: SparseVec = SparseVec::empty(self.dim);

        let confidence_scores: Vec<f64> = tag_embeddings.iter().map(|e| e.confidence).collect();
        let total_confidence: f64 = confidence_scores.iter().sum();
        let avg_confidence: f64 = total_confidence / (confidence_scores.len() as f64);

        for (c, e) in confidence_scores
            .into_iter()
            .zip(tag_embeddings.into_iter())
        {
            vec += &(e.vec.to_owned() * (c / total_confidence));
        }

        Some(Embedding::new(vec, avg_confidence))
    }

    pub fn push_status(&mut self, status: Status) {
        let mut status_embedding = Embedding::empty(self.dim);
        let tags: Vec<i64> = status.tags.iter().cloned().collect();

        if let Some(p_embedding) = self.producers.get(&status.account_id) {
            status_embedding.update(p_embedding);
        }

        if let Some(t_embedding) = self.get_weighted_tags_embedding(&tags) {
            status_embedding.update(&t_embedding);
        }

        self.statuses.insert(status.status_id, status_embedding);

        if !status.tags.is_empty() {
            self.statuses_tags.insert(status.status_id, tags);
        }

        // tracing::info!("Added status {}", status.status_id);
    }

    pub fn push_engagement(&mut self, engagement: Engagement) {
        let t_embedding = self.get_weighted_statuses_tags_embedding(&engagement.status_id);
        let tags = self.get_statuses_tags(&engagement.status_id);

        let a_embedding = self
            .consumers
            .entry(engagement.account_id)
            .or_insert_with(|| Embedding::empty(self.dim));

        if a_embedding.is_zero() {
            return;
        }

        if let Some(s_embedding) = self.statuses.get_mut(&engagement.status_id) {
            // 1. udpate status embedding
            s_embedding.update(a_embedding);

            // 2.1 udpate consumer embedding
            a_embedding.update(s_embedding);

            if let Some(t_embedding) = t_embedding {
                // 2.2 udpate consumer embedding
                a_embedding.update(&t_embedding);
            }
        }

        if let Some(p_embedding) = self.producers.get_mut(&engagement.status_id) {
            // 3. update producer embedding
            p_embedding.update(a_embedding);
        }

        for tag in tags {
            if let Some(t_embedding) = self.tags.get_mut(&tag) {
                // 4. update tag embedding
                t_embedding.update(a_embedding);
            }
        }

        // tracing::info!("Added engagement {} -> {}", engagement.account_id, engagement.status_id);
    }
}
