use std::collections::HashMap;

use crate::candidate::Candidate;

pub trait Scorer<Item, Ctx = ()>: Send + Sync {
    fn name(&self) -> &'static str {
        "unnamed"
    }

    fn score(&self, candidates: &mut [Candidate<Item>], ctx: &Ctx);
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

impl<Item, F, Ctx> Scorer<Item, Ctx> for Diversity<F>
where
    Item: Send + Sync,
    F: Fn(&Item) -> String + Send + Sync,
{
    fn name(&self) -> &'static str {
        "diversity"
    }

    fn score(&self, candidates: &mut [Candidate<Item>], _ctx: &Ctx) {
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
