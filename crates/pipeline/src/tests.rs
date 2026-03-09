use std::future::Future;
use std::pin::Pin;

use crate::candidate::Candidate;
use crate::filter::Filter;
use crate::pipeline::Pipeline;
use crate::sampler::TopK;
use crate::scorer::{Diversity, Scorer};
use crate::source::Source;

// --- Test item type ---

#[derive(Debug, Clone)]
struct Item {
    id: String,
    author: String,
    value: f64,
}

impl Item {
    fn new(id: &str, author: &str, value: f64) -> Self {
        Self {
            id: id.to_string(),
            author: author.to_string(),
            value,
        }
    }
}

// --- Test source ---

struct MockSource {
    name: &'static str,
    items: Vec<Item>,
}

impl MockSource {
    fn new(name: &'static str, items: Vec<Item>) -> Self {
        Self { name, items }
    }
}

impl Source<Item> for MockSource {
    fn name(&self) -> &'static str {
        self.name
    }

    fn collect(
        &self,
        limit: usize,
    ) -> Pin<Box<dyn Future<Output = Vec<Candidate<Item>>> + Send + '_>> {
        Box::pin(async move {
            self.items
                .iter()
                .take(limit)
                .map(|item| Candidate::new(item.clone(), self.name))
                .collect()
        })
    }
}

// --- Test scorer ---

struct ValueScorer;

impl Scorer<Item> for ValueScorer {
    fn score(&self, candidates: &mut [Candidate<Item>], _ctx: &()) {
        for c in candidates {
            c.score = c.item.value;
        }
    }
}

// --- Test filter ---

struct MinValueFilter {
    min: f64,
}

impl Filter<Item> for MinValueFilter {
    fn apply(&self, candidates: &mut Vec<Candidate<Item>>, _ctx: &()) {
        candidates.retain(|c| c.item.value >= self.min);
    }
}

// --- TopK tests ---

#[test]
fn topk_returns_highest_scored() {
    use crate::sampler::Sampler;

    let candidates = vec![
        scored_candidate("a", 10.0),
        scored_candidate("b", 50.0),
        scored_candidate("c", 30.0),
    ];

    let result = TopK.sample(candidates, 2);
    assert_eq!(result.len(), 2);
    assert_eq!(result[0].item.id, "b");
    assert_eq!(result[1].item.id, "c");
}

#[test]
fn topk_returns_all_when_fewer_than_n() {
    use crate::sampler::Sampler;

    let candidates = vec![scored_candidate("a", 10.0)];
    let result = TopK.sample(candidates, 5);
    assert_eq!(result.len(), 1);
}

#[test]
fn topk_handles_empty_input() {
    use crate::sampler::Sampler;

    let result: Vec<Candidate<Item>> = TopK.sample(Vec::new(), 10);
    assert!(result.is_empty());
}

// --- Diversity tests ---

#[test]
fn diversity_penalizes_repeated_keys() {
    let diversity = Diversity::new(0.1, |item: &Item| item.author.clone());

    let mut candidates = vec![
        scored_candidate_with_author("a", "alice", 100.0),
        scored_candidate_with_author("b", "alice", 100.0),
        scored_candidate_with_author("c", "bob", 100.0),
    ];

    diversity.score(&mut candidates, &());
    assert_eq!(candidates[0].score, 100.0);
    assert_eq!(candidates[1].score, 10.0);
    assert_eq!(candidates[2].score, 100.0);
}

#[test]
fn diversity_stacks_penalties() {
    let diversity = Diversity::new(0.1, |item: &Item| item.author.clone());

    let mut candidates = vec![
        scored_candidate_with_author("a", "alice", 100.0),
        scored_candidate_with_author("b", "alice", 100.0),
        scored_candidate_with_author("c", "alice", 100.0),
    ];

    diversity.score(&mut candidates, &());
    assert_eq!(candidates[0].score, 100.0);
    assert_eq!(candidates[1].score, 10.0);
    assert_eq!(candidates[2].score, 10.0);
}

// --- Filter tests ---

#[test]
fn filter_removes_items() {
    let filter = MinValueFilter { min: 5.0 };
    let mut candidates = vec![
        Candidate::new(Item::new("a", "alice", 10.0), "test"),
        Candidate::new(Item::new("b", "bob", 1.0), "test"),
        Candidate::new(Item::new("c", "carol", 7.0), "test"),
    ];

    filter.apply(&mut candidates, &());
    assert_eq!(candidates.len(), 2);
    assert_eq!(candidates[0].item.id, "a");
    assert_eq!(candidates[1].item.id, "c");
}

// --- Pipeline tests ---

#[tokio::test]
async fn pipeline_collects_scores_and_samples() {
    let pipeline = Pipeline::builder()
        .source(
            MockSource::new(
                "test",
                vec![
                    Item::new("a", "alice", 10.0),
                    Item::new("b", "bob", 50.0),
                    Item::new("c", "carol", 30.0),
                ],
            ),
            10,
        )
        .score(ValueScorer)
        .build();

    let result = pipeline.execute(2, &()).await;
    assert_eq!(result.len(), 2);
    assert_eq!(result[0].item.id, "b");
    assert_eq!(result[1].item.id, "c");
}

#[tokio::test]
async fn pipeline_filters_before_scoring() {
    let pipeline = Pipeline::builder()
        .source(
            MockSource::new(
                "test",
                vec![
                    Item::new("a", "alice", 1.0),
                    Item::new("b", "bob", 50.0),
                    Item::new("c", "carol", 30.0),
                ],
            ),
            10,
        )
        .filter(MinValueFilter { min: 5.0 })
        .score(ValueScorer)
        .build();

    let result = pipeline.execute(10, &()).await;
    assert_eq!(result.len(), 2);
    assert_eq!(result[0].item.id, "b");
    assert_eq!(result[1].item.id, "c");
}

#[tokio::test]
async fn pipeline_merges_multiple_sources() {
    let pipeline = Pipeline::builder()
        .source(
            MockSource::new("src1", vec![Item::new("a", "alice", 10.0)]),
            10,
        )
        .source(
            MockSource::new("src2", vec![Item::new("b", "bob", 20.0)]),
            10,
        )
        .score(ValueScorer)
        .build();

    let result = pipeline.execute(10, &()).await;
    assert_eq!(result.len(), 2);
    assert_eq!(result[0].item.id, "b");
    assert_eq!(result[1].item.id, "a");
}

#[tokio::test]
async fn pipeline_preserves_source_name() {
    let pipeline = Pipeline::builder()
        .source(
            MockSource::new("trending", vec![Item::new("a", "alice", 10.0)]),
            10,
        )
        .build();

    let result = pipeline.execute(10, &()).await;
    assert_eq!(result[0].source, "trending");
}

#[tokio::test]
async fn pipeline_respects_source_limit() {
    let pipeline = Pipeline::builder()
        .source(
            MockSource::new(
                "test",
                vec![
                    Item::new("a", "alice", 10.0),
                    Item::new("b", "bob", 20.0),
                    Item::new("c", "carol", 30.0),
                ],
            ),
            1,
        )
        .build();

    let result = pipeline.execute(10, &()).await;
    assert_eq!(result.len(), 1);
}

#[tokio::test]
async fn pipeline_empty_source_returns_empty() {
    let pipeline: Pipeline<Item> = Pipeline::builder()
        .source(MockSource::new("empty", Vec::new()), 10)
        .build();

    let result = pipeline.execute(10, &()).await;
    assert!(result.is_empty());
}

#[tokio::test]
async fn pipeline_with_diversity() {
    let pipeline = Pipeline::builder()
        .source(
            MockSource::new(
                "test",
                vec![
                    Item::new("a1", "alice", 100.0),
                    Item::new("a2", "alice", 90.0),
                    Item::new("b1", "bob", 80.0),
                ],
            ),
            10,
        )
        .score(ValueScorer)
        .score(Diversity::new(0.1, |item: &Item| item.author.clone()))
        .build();

    let result = pipeline.execute(3, &()).await;
    assert_eq!(result[0].item.id, "a1");
    assert_eq!(result[1].item.id, "b1");
    assert_eq!(result[2].item.id, "a2");
}

#[tokio::test]
async fn pipeline_is_reusable() {
    let pipeline = Pipeline::builder()
        .source(
            MockSource::new(
                "test",
                vec![Item::new("a", "alice", 10.0), Item::new("b", "bob", 20.0)],
            ),
            10,
        )
        .score(ValueScorer)
        .build();

    let r1 = pipeline.execute(1, &()).await;
    let r2 = pipeline.execute(1, &()).await;
    assert_eq!(r1[0].item.id, "b");
    assert_eq!(r2[0].item.id, "b");
}

// --- Context tests ---

struct UserCtx {
    blocked: Vec<String>,
}

struct BlockFilter;

impl Filter<Item, UserCtx> for BlockFilter {
    fn apply(&self, candidates: &mut Vec<Candidate<Item>>, ctx: &UserCtx) {
        candidates.retain(|c| !ctx.blocked.contains(&c.item.author));
    }
}

struct CtxValueScorer;

impl Scorer<Item, UserCtx> for CtxValueScorer {
    fn score(&self, candidates: &mut [Candidate<Item>], _ctx: &UserCtx) {
        for c in candidates {
            c.score = c.item.value;
        }
    }
}

#[tokio::test]
async fn pipeline_with_context() {
    let pipeline: Pipeline<Item, UserCtx> = Pipeline::builder()
        .source(
            MockSource::new(
                "test",
                vec![
                    Item::new("a", "alice", 50.0),
                    Item::new("b", "bob", 30.0),
                    Item::new("c", "carol", 10.0),
                ],
            ),
            10,
        )
        .filter(BlockFilter)
        .score(CtxValueScorer)
        .build();

    let ctx = UserCtx {
        blocked: vec!["alice".to_string()],
    };
    let result = pipeline.execute(10, &ctx).await;
    assert_eq!(result.len(), 2);
    assert_eq!(result[0].item.id, "b");
    assert_eq!(result[1].item.id, "c");
}

// --- Helpers ---

fn scored_candidate(id: &str, score: f64) -> Candidate<Item> {
    let mut c = Candidate::new(Item::new(id, "author", 0.0), "test");
    c.score = score;
    c
}

fn scored_candidate_with_author(id: &str, author: &str, score: f64) -> Candidate<Item> {
    let mut c = Candidate::new(Item::new(id, author, 0.0), "test");
    c.score = score;
    c
}
