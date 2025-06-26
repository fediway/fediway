use nalgebra_sparse::csr::CsrMatrix;
use std::collections::{HashMap, HashSet};
use sprs::CsVec;
use std::cmp;

use crate::algo::weighted_louvain::Communities;
use crate::models::{Engagement, Status};
use crate::sparse::{vec_scalar_mul, vec_add_assign};

const LAMBDA: f64 = 0.05;
const ALPHA: f64 = 0.01;
const BETA: f64 = 0.1;

pub struct Embedding {
    pub vec: CsVec<f64>,
    pub confidence: f64,
    updates: usize,
}

impl Embedding {
    pub fn empty(dim: usize) -> Self {
        Self {
            vec: CsVec::empty(dim),
            confidence: 0.0,
            updates: 0,
        }
    }

    pub fn new(dim: usize, vec: CsVec<f64>, confidence: f64) -> Self {
        Self {
            vec,
            confidence,
            updates: 0,
        }
    }

    pub fn update(&mut self, embedding: &Embedding) {
        let beta = (ALPHA * embedding.confidence).max(1.0 / ((self.updates as f64) + 1.0));
        self.vec *= 1.0 - beta;
        self.vec = &self.vec + &vec_scalar_mul(&embedding.vec, beta);
        self.updates += 1;
        self.confidence += (1.0 - self.confidence) * BETA * embedding.confidence;
    }
}

pub struct Embeddings {
    communities: Communities,
    consumer: HashMap<i64, Embedding>,
    producer: HashMap<i64, Embedding>,
    tags: HashMap<i64, Embedding>,
    statuses: HashMap<i64, Embedding>,
    statuses_tags: HashMap<i64, Vec<i64>>,
    dim: usize,
}

impl Embeddings {
    pub fn initial(
        communities: Communities,
        consumer: HashMap<i64, Embedding>,
        producer: HashMap<i64, Embedding>,
        tags: HashMap<i64, Embedding>,
    ) -> Self {
        Self {
            dim: communities.0.len(),
            communities,
            consumer,
            producer,
            tags,
            statuses: HashMap::new(),
            statuses_tags: HashMap::new()
        }
    }

    fn get_weighted_tags_embedding(&self, tags: &Vec<i64>) -> Option<Embedding> {
        let tag_embeddings: Vec<&Embedding> = tags
            .iter()
            .filter_map(|t| self.tags.get(t))
            .collect();

        if tag_embeddings.len() == 0 {
            return None;
        }

        let mut vec: CsVec<f64> = CsVec::empty(self.dim);

        let confidence_scores: Vec<f64> = tag_embeddings.iter().map(|e| e.confidence).collect();
        let total_confidence: f64 = confidence_scores.iter().sum();
        let avg_confidence: f64 = total_confidence / (confidence_scores.len() as f64);

        for (c, e) in confidence_scores.into_iter().zip(tag_embeddings.into_iter()) {
            vec = &vec + &vec_scalar_mul(&e.vec, (c / total_confidence));
        }   

        Some(Embedding::new(self.dim, vec, avg_confidence))
    }

    pub fn push_status(&mut self, status: Status) {
        let mut status_embedding = Embedding::empty(self.dim);
        let tags: Vec<i64> = status.tags.iter().cloned().collect();
        
        if let Some(p_embedding) = self.producer.get(&status.account_id) {
            status_embedding.update(p_embedding);
        }

        if let Some(t_embedding) = self.get_weighted_tags_embedding(&tags) {
            status_embedding.update(&t_embedding);
        }

        self.statuses.insert(status.status_id, status_embedding);

        if status.tags.len() > 0 {
            self.statuses_tags.insert(status.status_id, tags);
        }
    }

    pub fn push_engagement(&mut self, engagement: Engagement) {}
}
