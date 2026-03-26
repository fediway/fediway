use std::collections::HashSet;

use crate::candidate::Candidate;

pub trait Filter<Item, Ctx = ()>: Send + Sync {
    fn apply(&self, candidates: &mut Vec<Candidate<Item>>, ctx: &Ctx);
}

pub struct Dedup<F> {
    key_fn: F,
}

impl<F> Dedup<F> {
    pub fn new(key_fn: F) -> Self {
        Self { key_fn }
    }
}

impl<Item, F, Ctx> Filter<Item, Ctx> for Dedup<F>
where
    F: Fn(&Item) -> String + Send + Sync,
    Item: Send + Sync,
    Ctx: Send + Sync,
{
    fn apply(&self, candidates: &mut Vec<Candidate<Item>>, _ctx: &Ctx) {
        let mut seen = HashSet::new();
        candidates.retain(|c| seen.insert((self.key_fn)(&c.item)));
    }
}
