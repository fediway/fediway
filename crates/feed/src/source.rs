use crate::candidate::Candidate;

#[async_trait::async_trait]
pub trait Source<Item: Send>: Send + Sync {
    fn name(&self) -> &'static str;

    async fn collect(&self, limit: usize) -> Vec<Candidate<Item>>;
}
