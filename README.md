<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/logo-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset=".github/assets/logo-light.svg" />
    <img src=".github/assets/logo-light.svg" alt="Fediway" height="80" />
  </picture>
</p>

<p align="center">
  <a href="https://tally.so/r/vGMQll">Newsletter</a> ·
  <a href="https://about.fediway.com">About</a> ·
  <a href="https://github.com/sponsors/fediway/">Sponsor</a>
</p>

<p align="center">
Server-side algorithmic feeds for Mastodon instances. Local posts blended with content from external <a href="https://github.com/fediway/commonfeed">CommonFeed</a> providers.
</p>

<p align="center"><i>In open beta at <a href="https://fediway.com">fediway.com</a>. Expect breaking changes.</i></p>

## How it works

Every feed is a pipeline. Candidate sources collect posts from the local Mastodon database, from CommonFeed providers, or from anything implementing the `Source` trait. Filters drop what shouldn't be shown. Scorers reorder. A sampler produces the final slice, optionally enforcing per-group quotas so no single source dominates.

```rust
use feed::pipeline::Pipeline;
use feed::filter::Dedup;
use feed::quota_sampler::{QuotaSampler, GroupQuota};
use feed::scorer::Diversity;
use sources::mastodon::{NetworkSource, PolicyFilter};

let pipeline = Pipeline::builder()
    .name("timelines/home")
    .group("network",  [NetworkSource::new(/* ... */)], 180)
    .group("trending", trending_providers, 60)
    .filter(Dedup::new(|c| c.item.uri.clone().unwrap_or(c.item.url.clone())))
    .filter(PolicyFilter::new(policy))
    .score(Diversity::new(0.15, |p| p.author.handle.clone()))
    .sampler(QuotaSampler::new([
        GroupQuota::new("network",  0.70),
        GroupQuota::new("trending", 0.30),
    ]))
    .build();

let result = pipeline.execute(40, &()).await;
```

## Workspace

| Path | Description |
|------|-------------|
| `apps/server` | HTTP server (`fediway`). Serves feeds through the Mastodon API. |
| `apps/cli` | Operator CLI (`feedctl`). |
| `workers/orbit` | Personalization worker (`fediway-orbit`). |
| `crates/feed` | Pipeline primitives: sources, filters, scorers, samplers. |
| `crates/sources` | Built-in sources: local Mastodon, CommonFeed providers. |
| `crates/{state,mastodon,config,common}` | Storage, Mastodon types, config, shared types. |

## Quick start

Requires Rust stable, Postgres (Mastodon's database), and Redis.

```sh
cargo check --workspace
cargo test  --workspace
cargo run --bin fediway          # API server
cargo run --bin fediway-orbit    # personalization worker
```

A local Mastodon stack for development is in `docker-compose.integration.yaml`.

## Why this exists

The Fediverse has 1M+ monthly active users. Decentralized social media works. But it can't grow while new users see empty timelines and niche creators stay invisible. Chronological feeds aren't neutral: they privilege the frequent over the thoughtful, the recent over the relevant, the loud over the good.

Algorithms are tools. The question isn't whether to use them, but whether you can see, modify, and trust them. Fediway runs server-side, inside the instance, on infrastructure the operator controls. No browser extensions, no API keys, no third-party services. Operators decide which sources, filters, scorers, and samplers run, and can replace any of them.

More at [about.fediway.com](https://about.fediway.com).

## Alternatives

Existing options run client-side: [BYOTA](https://github.com/mozilla-ai/byota) (Mozilla's research project), [fedialgo](https://github.com/pkreissel/fedialgo) (customizable reranker), [fediview](https://github.com/adamghill/fediview) and [Mastodon Digest](https://github.com/hodgesmr/mastodon_digest) (digest generators). Each requires the user to install something. Fediway is the only server-side option, deployed once per instance and transparent to clients.
