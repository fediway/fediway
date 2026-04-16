use std::cmp::Ordering;

use crate::candidate::Candidate;

pub trait Sampler<Item>: Send + Sync {
    fn pick(&self, remaining: &[Candidate<Item>], selected: &[Candidate<Item>]) -> Option<usize>;
}

pub fn sample<Item>(
    sampler: &dyn Sampler<Item>,
    mut candidates: Vec<Candidate<Item>>,
    n: usize,
) -> Vec<Candidate<Item>> {
    let mut selected = Vec::with_capacity(n.min(candidates.len()));
    for _ in 0..n {
        if candidates.is_empty() {
            break;
        }
        let Some(idx) = sampler.pick(&candidates, &selected) else {
            break;
        };
        selected.push(candidates.swap_remove(idx));
    }
    selected
}

pub struct TopK;

impl<Item: Send + Sync> Sampler<Item> for TopK {
    fn pick(&self, remaining: &[Candidate<Item>], _selected: &[Candidate<Item>]) -> Option<usize> {
        remaining
            .iter()
            .enumerate()
            .max_by(|a, b| a.1.score.partial_cmp(&b.1.score).unwrap_or(Ordering::Equal))
            .map(|(i, _)| i)
    }
}
