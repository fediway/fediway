# feed

Composable feed engine: **collect → filter → score → sample**.

```
Feed<Item, Ctx = ()>
  ├── Source<Item>      — fetches candidates (runs concurrently)
  ├── Filter<Item, Ctx> — removes candidates based on context
  ├── Scorer<Item, Ctx> — adjusts candidate scores
  └── Sampler<Item>     — selects final output (default: TopK)
```

## Usage

```rust
let feed = Feed::builder()
    .name("trends/statuses")
    .source(MySource::new(db.clone()), 100)
    .source(AnotherSource::new(api), 50)
    .filter(BlockedAuthorsFilter)
    .score(EngagementScorer)
    .score(Diversity::new(0.1, |post: &Post| post.author.id.clone()))
    .build();

let result = feed.execute(20, &user_ctx).await;
// result.items — final candidates
// result.collected — total before filtering
```

## Traits

```rust
// Fetch candidates — sources run concurrently via join_all
trait Source<Item: Send>: Send + Sync {
    fn name(&self) -> &'static str;
    fn collect(&self, limit: usize) -> Pin<Box<dyn Future<Output = Vec<Candidate<Item>>> + Send + '_>>;
}

// Remove unwanted candidates
trait Filter<Item, Ctx = ()>: Send + Sync {
    fn apply(&self, candidates: &mut Vec<Candidate<Item>>, ctx: &Ctx);
}

// Adjust scores — runs in order, each scorer sees previous scores
trait Scorer<Item, Ctx = ()>: Send + Sync {
    fn score(&self, candidates: &mut [Candidate<Item>], ctx: &Ctx);
}

// Select final output from scored candidates
trait Sampler<Item>: Send + Sync {
    fn sample(&self, candidates: Vec<Candidate<Item>>, n: usize) -> Vec<Candidate<Item>>;
}
```

## Context

`Ctx` carries per-request data (user preferences, blocked authors, seen posts). Defaults to `()` when not needed.

```rust
struct UserCtx {
    blocked: Vec<String>,
    seen: HashSet<String>,
}

let feed: Feed<Post, UserCtx> = Feed::builder()
    .name("home")
    .source(trending, 100)
    .filter(SeenFilter)       // must impl Filter<Post, UserCtx>
    .score(PersonalBoost)     // must impl Scorer<Post, UserCtx>
    .build();
```

## Observability

Every execution emits metrics via the `metrics` crate (zero-cost no-ops when no recorder is installed). All metrics carry a `feed` label from `Feed::builder().name("...")`:

- `fediway_feed_source_candidates{feed, source}` — candidates per source
- `fediway_feed_source_duration_seconds{feed, source}` — fetch time per source
- `fediway_feed_scorer_duration_seconds{feed, scorer}` — time per scoring pass
- `fediway_feed_collected{feed}` / `fediway_feed_filtered{feed}` / `fediway_feed_returned{feed}` — full funnel
- `fediway_feed_duration_seconds{feed}` — total execution time

The `Scorer` trait provides `fn name() -> &'static str` (default `"unnamed"`) for scorer identification in metrics.

## Built-in

- **`TopK`** — default sampler, returns top N by score
- **`Diversity::new(penalty, key_fn)`** — penalizes repeated keys (e.g. same author)
