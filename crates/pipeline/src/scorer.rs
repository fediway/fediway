use std::collections::HashMap;

use crate::candidate::Candidate;

pub trait Scorer<T, Ctx = ()>: Send + Sync {
    fn score(&self, candidates: &mut [Candidate<T>], ctx: &Ctx);
}

pub struct Diversity<F> {
    penalty: f64,
    key_fn: F,
}

impl<F> Diversity<F> {
    #[must_use]
    pub fn new(penalty: f64, key_fn: F) -> Self {
        Self { penalty, key_fn }
    }
}

impl<T, F, Ctx> Scorer<T, Ctx> for Diversity<F>
where
    T: Send + Sync,
    F: Fn(&T) -> String + Send + Sync,
{
    fn score(&self, candidates: &mut [Candidate<T>], _ctx: &Ctx) {
        let mut seen: HashMap<String, usize> = HashMap::new();
        for candidate in candidates {
            let key = (self.key_fn)(&candidate.item);
            let count = seen.entry(key).or_insert(0);
            if *count > 0 {
                candidate.score *= self.penalty;
            }
            *count += 1;
        }
    }
}
