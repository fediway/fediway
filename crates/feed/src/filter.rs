use crate::candidate::Candidate;

pub trait Filter<Item, Ctx = ()>: Send + Sync {
    fn apply(&self, candidates: &mut Vec<Candidate<Item>>, ctx: &Ctx);
}
