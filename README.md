# Fediway

Algorithmic feeds for Mastodon instances. Replaces chronological timelines with configurable, ranked feeds that blend local content with external content providers.

## Quick start

```sh
cargo check --workspace       # verify everything compiles
cargo test --workspace        # run tests
cargo run --bin fediway        # start the server
cargo run --bin fediway-worker # start the background worker
```

## Requirements

- Rust stable (latest)
- Access to Mastodon's PostgreSQL
- Redis
