use futures::future::join_all;
use tracing::info;

use crate::candidate::Candidate;
use crate::filter::Filter;
use crate::sampler::{Sampler, TopK};
use crate::scorer::Scorer;
use crate::source::Source;

pub struct Pipeline<T: Send, Ctx = ()> {
    sources: Vec<(Box<dyn Source<T>>, usize)>,
    filters: Vec<Box<dyn Filter<T, Ctx>>>,
    scorers: Vec<Box<dyn Scorer<T, Ctx>>>,
    sampler: Box<dyn Sampler<T>>,
}

impl<T: Send + Sync + 'static, Ctx: Send + Sync + 'static> Pipeline<T, Ctx> {
    #[must_use]
    pub fn builder() -> PipelineBuilder<T, Ctx> {
        PipelineBuilder::new()
    }

    pub async fn execute(&self, limit: usize, ctx: &Ctx) -> Vec<Candidate<T>> {
        let mut candidates = self.collect().await;
        info!(count = candidates.len(), "candidates collected");

        for filter in &self.filters {
            filter.apply(&mut candidates, ctx);
        }
        info!(count = candidates.len(), "after filtering");

        for scorer in &self.scorers {
            scorer.score(&mut candidates, ctx);
        }

        self.sampler.sample(candidates, limit)
    }

    async fn collect(&self) -> Vec<Candidate<T>> {
        let futures: Vec<_> = self
            .sources
            .iter()
            .map(|(source, limit)| {
                let name = source.name();
                let limit = *limit;
                async move {
                    let batch = source.collect(limit).await;
                    info!(source = name, count = batch.len(), "source collected");
                    batch
                }
            })
            .collect();

        join_all(futures).await.into_iter().flatten().collect()
    }
}

pub struct PipelineBuilder<T: Send, Ctx = ()> {
    sources: Vec<(Box<dyn Source<T>>, usize)>,
    filters: Vec<Box<dyn Filter<T, Ctx>>>,
    scorers: Vec<Box<dyn Scorer<T, Ctx>>>,
    sampler: Option<Box<dyn Sampler<T>>>,
}

impl<T: Send + Sync + 'static, Ctx: Send + Sync + 'static> PipelineBuilder<T, Ctx> {
    fn new() -> Self {
        Self {
            sources: Vec::new(),
            filters: Vec::new(),
            scorers: Vec::new(),
            sampler: None,
        }
    }

    #[must_use]
    pub fn source(mut self, source: impl Source<T> + 'static, limit: usize) -> Self {
        self.sources.push((Box::new(source), limit));
        self
    }

    #[must_use]
    pub fn sources(
        mut self,
        sources: impl IntoIterator<Item = impl Source<T> + 'static>,
        limit: usize,
    ) -> Self {
        for source in sources {
            self.sources.push((Box::new(source), limit));
        }
        self
    }

    #[must_use]
    pub fn filter(mut self, filter: impl Filter<T, Ctx> + 'static) -> Self {
        self.filters.push(Box::new(filter));
        self
    }

    #[must_use]
    pub fn score(mut self, scorer: impl Scorer<T, Ctx> + 'static) -> Self {
        self.scorers.push(Box::new(scorer));
        self
    }

    #[must_use]
    pub fn sampler(mut self, sampler: impl Sampler<T> + 'static) -> Self {
        self.sampler = Some(Box::new(sampler));
        self
    }

    #[must_use]
    pub fn build(self) -> Pipeline<T, Ctx> {
        Pipeline {
            sources: self.sources,
            filters: self.filters,
            scorers: self.scorers,
            sampler: self.sampler.unwrap_or_else(|| Box::new(TopK)),
        }
    }
}
