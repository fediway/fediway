use std::cmp::Ordering;

use crate::candidate::Candidate;

pub trait Sampler<Item>: Send + Sync {
    fn sample(&self, candidates: Vec<Candidate<Item>>, n: usize) -> Vec<Candidate<Item>>;
}

pub struct TopK;

impl<Item: Send + Sync> Sampler<Item> for TopK {
    fn sample(&self, mut candidates: Vec<Candidate<Item>>, n: usize) -> Vec<Candidate<Item>> {
        candidates.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        candidates.truncate(n);
        candidates
    }
}
