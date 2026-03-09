use std::cmp::Ordering;

use crate::candidate::Candidate;

pub trait Sampler<T>: Send + Sync {
    fn sample(&self, candidates: Vec<Candidate<T>>, n: usize) -> Vec<Candidate<T>>;
}

pub struct TopK;

impl<T: Send + Sync> Sampler<T> for TopK {
    fn sample(&self, mut candidates: Vec<Candidate<T>>, n: usize) -> Vec<Candidate<T>> {
        candidates.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        candidates.truncate(n);
        candidates
    }
}
