use std::collections::HashSet;

use crate::candidate::Candidate;

pub trait Filter<Item, Ctx = ()>: Send + Sync {
    fn apply(&self, candidates: &mut Vec<Candidate<Item>>, ctx: &Ctx);
}

type KeyFn<Item> = Box<dyn Fn(&Candidate<Item>) -> String + Send + Sync>;
type PriorityFn<Item> = Box<dyn Fn(&Candidate<Item>) -> i32 + Send + Sync>;

/// Deduplicates candidates by a string key extracted from each
/// [`Candidate`]. By default, the first occurrence wins in the order
/// candidates arrive at the filter. Use [`Dedup::prefer`] to specify
/// a priority function — lower values win when duplicates collide,
/// making it possible to express "prefer local over remote for the
/// same URI."
///
/// The key function receives the full `Candidate`, not just the inner
/// `Item`, so you can key on candidate metadata like `group` or
/// `source` when needed.
pub struct Dedup<Item> {
    key_fn: KeyFn<Item>,
    priority_fn: PriorityFn<Item>,
}

impl<Item: Send + Sync + 'static> Dedup<Item> {
    pub fn new<K>(key_fn: K) -> Self
    where
        K: Fn(&Candidate<Item>) -> String + Send + Sync + 'static,
    {
        Self {
            key_fn: Box::new(key_fn),
            priority_fn: Box::new(|_| 0),
        }
    }

    #[must_use]
    pub fn prefer<P>(mut self, priority_fn: P) -> Self
    where
        P: Fn(&Candidate<Item>) -> i32 + Send + Sync + 'static,
    {
        self.priority_fn = Box::new(priority_fn);
        self
    }
}

impl<Item, Ctx> Filter<Item, Ctx> for Dedup<Item>
where
    Item: Send + Sync,
    Ctx: Send + Sync,
{
    fn apply(&self, candidates: &mut Vec<Candidate<Item>>, _ctx: &Ctx) {
        candidates.sort_by_key(|c| (self.priority_fn)(c));
        let mut seen = HashSet::new();
        candidates.retain(|c| seen.insert((self.key_fn)(c)));
    }
}
