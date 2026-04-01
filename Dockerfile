FROM lukemathwalker/cargo-chef:0.1.77-rust-1.94.0-slim-bookworm AS chef

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       pkg-config libssl-dev make g++ mold \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM chef AS planner

COPY . .
RUN cargo chef prepare --recipe-path recipe.json

FROM chef AS builder

ENV RUSTFLAGS="-C link-arg=-fuse-ld=mold"

COPY --from=planner /app/recipe.json recipe.json
RUN cargo chef cook --release --recipe-path recipe.json

COPY . .
RUN cargo build --release --workspace

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libssl3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --no-log-init app

COPY --from=builder /app/target/release/fediway /usr/local/bin/
COPY --from=builder /app/target/release/fediway-orbit /usr/local/bin/
COPY --from=builder /app/target/release/feedctl /usr/local/bin/

USER app
