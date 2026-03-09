use crate::candidate::Candidate;

pub trait Filter<T, Ctx = ()>: Send + Sync {
    fn apply(&self, candidates: &mut Vec<Candidate<T>>, ctx: &Ctx);
}
