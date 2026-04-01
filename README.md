<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/logo-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset=".github/assets/logo-light.svg" />
    <img src=".github/assets/logo-light.svg" alt="Fediway" height="80" />
  </picture>
</p>

<p align="center">
Algorithmic feeds for Mastodon instances. Replaces chronological timelines with configurable, ranked feeds that blend local content with external content providers.
</p>

## Quick start

```sh
cargo check --workspace       # verify everything compiles
cargo test --workspace        # run tests
cargo run --bin fediway        # start the server
cargo run --bin fediway-orbit  # start the orbit worker
```

## Requirements

- Rust stable (latest)
- Access to Mastodon's PostgreSQL
- Redis
