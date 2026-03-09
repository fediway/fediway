# pipeline

Generic, composable ranking pipeline: **collect → filter → score → sample**.

```
Pipeline<T, Ctx = ()>
  ├── Source<T>         — fetches candidates (runs concurrently)
  ├── Filter<T, Ctx>    — removes candidates based on context
  ├── Scorer<T, Ctx>    — adjusts candidate scores
  └── Sampler<T>        — selects final output (default: TopK)
```

## Usage

```rust
let pipeline = Pipeline::builder()
    .source(MySource::new(db.clone()), 100)
    .source(AnotherSource::new(api), 50)
    .filter(BlockedAuthorsFilter)
    .score(EngagementScorer)
    .score(Diversity::new(0.1, |post: &Post| post.author.id.clone()))
    .build();

let results = pipeline.execute(20, &user_ctx).await;
```

## Traits

```rust
// Fetch candidates — sources run concurrently via join_all
trait Source<T: Send>: Send + Sync {
    fn name(&self) -> &'static str;
    fn collect(&self, limit: usize) -> Pin<Box<dyn Future<Output = Vec<Candidate<T>>> + Send + '_>>;
}

// Remove unwanted candidates
trait Filter<T, Ctx = ()>: Send + Sync {
    fn apply(&self, candidates: &mut Vec<Candidate<T>>, ctx: &Ctx);
}

// Adjust scores — runs in order, each scorer sees previous scores
trait Scorer<T, Ctx = ()>: Send + Sync {
    fn score(&self, candidates: &mut [Candidate<T>], ctx: &Ctx);
}

// Select final output from scored candidates
trait Sampler<T>: Send + Sync {
    fn sample(&self, candidates: Vec<Candidate<T>>, n: usize) -> Vec<Candidate<T>>;
}
```

## Context

`Ctx` carries per-request data (user preferences, blocked authors, seen posts). Defaults to `()` when not needed.

```rust
struct UserCtx {
    blocked: Vec<String>,
    seen: HashSet<String>,
}

let pipeline: Pipeline<Post, UserCtx> = Pipeline::builder()
    .source(trending, 100)
    .filter(SeenFilter)       // must impl Filter<Post, UserCtx>
    .score(PersonalBoost)     // must impl Scorer<Post, UserCtx>
    .build();
```

## Built-in

- **`TopK`** — default sampler, returns top N by score
- **`Diversity::new(penalty, key_fn)`** — penalizes repeated keys (e.g. same author)
