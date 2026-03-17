use crate::candidate::Candidate;
use crate::cursor::Offset;
use crate::feed::{Feed, FeedResult};
use crate::filter::Filter;
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

#[async_trait::async_trait]
impl Source<Item> for MockSource {
    fn name(&self) -> &'static str {
        self.name
    }

    async fn collect(&self, limit: usize) -> Vec<Candidate<Item>> {
        self.items
            .iter()
            .take(limit)
            .map(|item| Candidate::new(item.clone(), self.name))
            .collect()
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
    assert!((candidates[0].score - 100.0).abs() < f64::EPSILON);
    assert!((candidates[1].score - 10.0).abs() < f64::EPSILON);
    assert!((candidates[2].score - 100.0).abs() < f64::EPSILON);
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
    assert!((candidates[0].score - 100.0).abs() < f64::EPSILON);
    assert!((candidates[1].score - 10.0).abs() < f64::EPSILON);
    assert!((candidates[2].score - 10.0).abs() < f64::EPSILON);
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

// --- Feed tests ---

#[tokio::test]
async fn feed_collects_scores_and_samples() {
    let feed = Feed::builder()
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

    let result = feed.execute(2, &()).await;
    assert_eq!(result.items.len(), 2);
    assert_eq!(result.items[0].item.id, "b");
    assert_eq!(result.items[1].item.id, "c");
}

#[tokio::test]
async fn feed_filters_before_scoring() {
    let feed = Feed::builder()
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

    let result = feed.execute(10, &()).await;
    assert_eq!(result.items.len(), 2);
    assert_eq!(result.items[0].item.id, "b");
    assert_eq!(result.items[1].item.id, "c");
}

#[tokio::test]
async fn feed_merges_multiple_sources() {
    let feed = Feed::builder()
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

    let result = feed.execute(10, &()).await;
    assert_eq!(result.items.len(), 2);
    assert_eq!(result.items[0].item.id, "b");
    assert_eq!(result.items[1].item.id, "a");
}

#[tokio::test]
async fn feed_preserves_source_name() {
    let feed = Feed::builder()
        .source(
            MockSource::new("trending", vec![Item::new("a", "alice", 10.0)]),
            10,
        )
        .build();

    let result = feed.execute(10, &()).await;
    assert_eq!(result.items[0].source, "trending");
}

#[tokio::test]
async fn feed_respects_source_limit() {
    let feed = Feed::builder()
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

    let result = feed.execute(10, &()).await;
    assert_eq!(result.items.len(), 1);
}

#[tokio::test]
async fn feed_empty_source_returns_empty() {
    let feed: Feed<Item> = Feed::builder()
        .source(MockSource::new("empty", Vec::new()), 10)
        .build();

    let result = feed.execute(10, &()).await;
    assert!(result.items.is_empty());
}

#[tokio::test]
async fn feed_with_diversity() {
    let feed = Feed::builder()
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

    let result = feed.execute(3, &()).await;
    assert_eq!(result.items[0].item.id, "a1");
    assert_eq!(result.items[1].item.id, "b1");
    assert_eq!(result.items[2].item.id, "a2");
}

#[tokio::test]
async fn feed_is_reusable() {
    let feed = Feed::builder()
        .source(
            MockSource::new(
                "test",
                vec![Item::new("a", "alice", 10.0), Item::new("b", "bob", 20.0)],
            ),
            10,
        )
        .score(ValueScorer)
        .build();

    let r1 = feed.execute(1, &()).await;
    let r2 = feed.execute(1, &()).await;
    assert_eq!(r1.items[0].item.id, "b");
    assert_eq!(r2.items[0].item.id, "b");
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
async fn feed_with_context() {
    let feed: Feed<Item, UserCtx> = Feed::builder()
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
    let result = feed.execute(10, &ctx).await;
    assert_eq!(result.items.len(), 2);
    assert_eq!(result.items[0].item.id, "b");
    assert_eq!(result.items[1].item.id, "c");
}

// --- Pagination tests ---

#[test]
fn paginate_first_page() {
    let result = FeedResult {
        items: vec![
            scored_candidate("a", 5.0),
            scored_candidate("b", 4.0),
            scored_candidate("c", 3.0),
            scored_candidate("d", 2.0),
            scored_candidate("e", 1.0),
        ],
        collected: 5,
    };
    let page = result.paginate(2, &Offset::parse(None));
    assert_eq!(page.items.len(), 2);
    assert_eq!(page.items[0].item.id, "a");
    assert_eq!(page.items[1].item.id, "b");
    assert!(page.has_more);
    assert_eq!(page.cursor.as_deref(), Some("2"));
}

#[test]
fn paginate_second_page() {
    let result = FeedResult {
        items: vec![
            scored_candidate("a", 5.0),
            scored_candidate("b", 4.0),
            scored_candidate("c", 3.0),
            scored_candidate("d", 2.0),
            scored_candidate("e", 1.0),
        ],
        collected: 5,
    };
    let page = result.paginate(2, &Offset::parse(Some("2")));
    assert_eq!(page.items.len(), 2);
    assert_eq!(page.items[0].item.id, "c");
    assert_eq!(page.items[1].item.id, "d");
    assert!(page.has_more);
    assert_eq!(page.cursor.as_deref(), Some("4"));
}

#[test]
fn paginate_last_page() {
    let result = FeedResult {
        items: vec![
            scored_candidate("a", 3.0),
            scored_candidate("b", 2.0),
            scored_candidate("c", 1.0),
        ],
        collected: 3,
    };
    let page = result.paginate(2, &Offset::parse(Some("2")));
    assert_eq!(page.items.len(), 1);
    assert_eq!(page.items[0].item.id, "c");
    assert!(!page.has_more);
    assert!(page.cursor.is_none());
}

#[test]
fn paginate_beyond_end() {
    let result = FeedResult {
        items: vec![scored_candidate("a", 1.0)],
        collected: 1,
    };
    let page = result.paginate(10, &Offset::parse(Some("100")));
    assert!(page.items.is_empty());
    assert!(!page.has_more);
    assert!(page.cursor.is_none());
}

#[test]
fn paginate_invalid_cursor_starts_at_zero() {
    let result = FeedResult {
        items: vec![scored_candidate("a", 2.0), scored_candidate("b", 1.0)],
        collected: 2,
    };
    let page = result.paginate(1, &Offset::parse(Some("garbage")));
    assert_eq!(page.items[0].item.id, "a");
    assert!(page.has_more);
}

#[test]
fn paginate_empty_result() {
    let result: FeedResult<Item> = FeedResult {
        items: vec![],
        collected: 0,
    };
    let page = result.paginate(20, &Offset::parse(None));
    assert!(page.items.is_empty());
    assert!(!page.has_more);
    assert!(page.cursor.is_none());
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
