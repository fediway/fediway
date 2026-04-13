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

pub struct PipelineResult<Item> {
    pub items: Vec<Candidate<Item>>,
    pub collected: usize,
}

pub struct Page<Item> {
    pub items: Vec<Candidate<Item>>,
    pub cursor: Option<String>,
    pub has_more: bool,
}

impl<Item> PipelineResult<Item> {
    #[must_use]
    pub fn paginate(self, limit: usize, cursor: &impl Cursor<Item>) -> Page<Item> {
        cursor.paginate(self.items, limit)
    }
}

struct SourceSpec<Item: Send, Ctx = ()> {
    source: Box<dyn Source<Item>>,
    limit: usize,
    override_group: Option<&'static str>,
    _ctx: std::marker::PhantomData<Ctx>,
}

pub struct Pipeline<Item: Send, Ctx = ()> {
    name: &'static str,
    sources: Vec<SourceSpec<Item, Ctx>>,
    fallback: Vec<SourceSpec<Item, Ctx>>,
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

        let mut candidates = self.collect(&self.sources).await;
        let collected = candidates.len();
        info!(
            pipeline = self.name,
            count = collected,
            "candidates collected"
        );

        if !self.fallback.is_empty() && candidates.len() < limit / 2 {
            let fallback = self.collect(&self.fallback).await;
            info!(
                pipeline = self.name,
                count = fallback.len(),
                "fallback activated"
            );
            candidates.extend(fallback);
        }

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

    async fn collect(&self, specs: &[SourceSpec<Item, Ctx>]) -> Vec<Candidate<Item>> {
        let pipeline_name = self.name;
        let futures: Vec<_> = specs
            .iter()
            .map(|spec| {
                let name = spec.source.name();
                let limit = spec.limit;
                let override_group = spec.override_group;
                async move {
                    let start = Instant::now();
                    let mut batch = spec.source.collect(limit).await;
                    if let Some(group) = override_group {
                        for c in &mut batch {
                            c.group = group;
                        }
                    }
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
    sources: Vec<SourceSpec<Item, Ctx>>,
    fallback: Vec<SourceSpec<Item, Ctx>>,
    filters: Vec<Box<dyn Filter<Item, Ctx>>>,
    scorers: Vec<Box<dyn Scorer<Item, Ctx>>>,
    sampler: Option<Box<dyn Sampler<Item>>>,
}

impl<Item: Send + Sync + 'static, Ctx: Send + Sync + 'static> PipelineBuilder<Item, Ctx> {
    fn new() -> Self {
        Self {
            name: "unnamed",
            sources: Vec::new(),
            fallback: Vec::new(),
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
        self.sources.push(SourceSpec {
            source: Box::new(source),
            limit,
            override_group: None,
            _ctx: std::marker::PhantomData,
        });
        self
    }

    #[must_use]
    pub fn sources(
        mut self,
        sources: impl IntoIterator<Item = impl Source<Item> + 'static>,
        limit: usize,
    ) -> Self {
        for source in sources {
            self.sources.push(SourceSpec {
                source: Box::new(source),
                limit,
                override_group: None,
                _ctx: std::marker::PhantomData,
            });
        }
        self
    }

    /// Add sources tagged with an explicit group name. The group overrides
    /// whatever each source's candidates would otherwise report, so the
    /// sampler (e.g. `QuotaSampler`) can enforce quotas against this name.
    #[must_use]
    pub fn group(
        mut self,
        group: &'static str,
        sources: impl IntoIterator<Item = impl Source<Item> + 'static>,
        limit: usize,
    ) -> Self {
        for source in sources {
            self.sources.push(SourceSpec {
                source: Box::new(source),
                limit,
                override_group: Some(group),
                _ctx: std::marker::PhantomData,
            });
        }
        self
    }

    /// Register fallback sources that are only collected when the main
    /// pool comes up short (< limit / 2 after main collection). Fallback
    /// candidates are tagged with group `"_fallback"` so samplers can
    /// treat them differently from primary groups.
    #[must_use]
    pub fn fallback(
        mut self,
        sources: impl IntoIterator<Item = impl Source<Item> + 'static>,
        limit: usize,
    ) -> Self {
        for source in sources {
            self.fallback.push(SourceSpec {
                source: Box::new(source),
                limit,
                override_group: Some("_fallback"),
                _ctx: std::marker::PhantomData,
            });
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
            fallback: self.fallback,
            filters: self.filters,
            scorers: self.scorers,
            sampler: self.sampler.unwrap_or_else(|| Box::new(TopK)),
        }
    }
}
