use std::future::Future;
use std::pin::Pin;

use crate::candidate::Candidate;

pub trait Source<T: Send>: Send + Sync {
    fn name(&self) -> &'static str;

    fn collect(&self, limit: usize)
    -> Pin<Box<dyn Future<Output = Vec<Candidate<T>>> + Send + '_>>;
}
