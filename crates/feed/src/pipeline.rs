use std::time::Instant;

use futures::future::join_all;
use tracing::info;

use crate::candidate::Candidate;
use crate::cursor::Cursor;
use crate::filter::Filter;
use crate::observe;
use crate::sampler::{Sampler, TopK};
use crate::scorer::Scorer;
use crate::source::Source;

/// Result of a pipeline execution with metadata for observability.
pub struct PipelineResult<Item> {
    pub items: Vec<Candidate<Item>>,
    pub collected: usize,
}

/// A paginated slice of a pipeline result.
pub struct Page<Item> {
    pub items: Vec<Candidate<Item>>,
    pub cursor: Option<String>,
    pub has_more: bool,
}

impl<Item> PipelineResult<Item> {
    /// Paginate the result using the given cursor strategy.
    #[must_use]
    pub fn paginate(self, limit: usize, cursor: &impl Cursor<Item>) -> Page<Item> {
        cursor.paginate(self.items, limit)
    }
}

pub struct Pipeline<Item: Send, Ctx = ()> {
    name: &'static str,
    sources: Vec<(Box<dyn Source<Item>>, usize)>,
    filters: Vec<Box<dyn Filter<Item, Ctx>>>,
    scorers: Vec<Box<dyn Scorer<Item, Ctx>>>,
    sampler: Box<dyn Sampler<Item>>,
}

impl<Item: Send + Sync + 'static, Ctx: Send + Sync + 'static> Pipeline<Item, Ctx> {
    #[must_use]
    pub fn builder() -> PipelineBuilder<Item, Ctx> {
        PipelineBuilder::new()
    }

    pub async fn execute(&self, limit: usize, ctx: &Ctx) -> PipelineResult<Item> {
        let start = Instant::now();

        let mut candidates = self.collect().await;
        let collected = candidates.len();
        info!(
            pipeline = self.name,
            count = collected,
            "candidates collected"
        );

        for filter in &self.filters {
            filter.apply(&mut candidates, ctx);
        }
        let filtered = candidates.len();
        info!(pipeline = self.name, count = filtered, "after filtering");

        for scorer in &self.scorers {
            let scorer_start = Instant::now();
            scorer.score(&mut candidates, ctx);
            observe::scorer_applied(self.name, scorer.name(), scorer_start.elapsed());
        }

        let items = self.sampler.sample(candidates, limit);

        observe::executed(self.name, collected, filtered, items.len(), start.elapsed());

        PipelineResult { items, collected }
    }

    async fn collect(&self) -> Vec<Candidate<Item>> {
        let pipeline_name = self.name;
        let futures: Vec<_> = self
            .sources
            .iter()
            .map(|(source, limit)| {
                let name = source.name();
                let limit = *limit;
                async move {
                    let start = Instant::now();
                    let batch = source.collect(limit).await;
                    observe::source_collected(pipeline_name, name, batch.len(), start.elapsed());
                    info!(
                        pipeline = pipeline_name,
                        source = name,
                        count = batch.len(),
                        "source collected"
                    );
                    batch
                }
            })
            .collect();

        join_all(futures).await.into_iter().flatten().collect()
    }
}

pub struct PipelineBuilder<Item: Send, Ctx = ()> {
    name: &'static str,
    sources: Vec<(Box<dyn Source<Item>>, usize)>,
    filters: Vec<Box<dyn Filter<Item, Ctx>>>,
    scorers: Vec<Box<dyn Scorer<Item, Ctx>>>,
    sampler: Option<Box<dyn Sampler<Item>>>,
}

impl<Item: Send + Sync + 'static, Ctx: Send + Sync + 'static> PipelineBuilder<Item, Ctx> {
    fn new() -> Self {
        Self {
            name: "unnamed",
            sources: Vec::new(),
            filters: Vec::new(),
            scorers: Vec::new(),
            sampler: None,
        }
    }

    #[must_use]
    pub fn name(mut self, name: &'static str) -> Self {
        self.name = name;
        self
    }

    #[must_use]
    pub fn source(mut self, source: impl Source<Item> + 'static, limit: usize) -> Self {
        self.sources.push((Box::new(source), limit));
        self
    }

    #[must_use]
    pub fn sources(
        mut self,
        sources: impl IntoIterator<Item = impl Source<Item> + 'static>,
        limit: usize,
    ) -> Self {
        for source in sources {
            self.sources.push((Box::new(source), limit));
        }
        self
    }

    #[must_use]
    pub fn filter(mut self, filter: impl Filter<Item, Ctx> + 'static) -> Self {
        self.filters.push(Box::new(filter));
        self
    }

    #[must_use]
    pub fn score(mut self, scorer: impl Scorer<Item, Ctx> + 'static) -> Self {
        self.scorers.push(Box::new(scorer));
        self
    }

    #[must_use]
    pub fn sampler(mut self, sampler: impl Sampler<Item> + 'static) -> Self {
        self.sampler = Some(Box::new(sampler));
        self
    }

    #[must_use]
    pub fn build(self) -> Pipeline<Item, Ctx> {
        Pipeline {
            name: self.name,
            sources: self.sources,
            filters: self.filters,
            scorers: self.scorers,
            sampler: self.sampler.unwrap_or_else(|| Box::new(TopK)),
        }
    }
}
