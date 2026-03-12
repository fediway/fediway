FROM rust:1.94-slim-bookworm AS chef

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN cargo install cargo-chef --locked
WORKDIR /app

FROM chef AS planner

COPY . .
RUN cargo chef prepare --recipe-path recipe.json

FROM chef AS builder

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

COPY --from=builder /app/target/release/server /usr/local/bin/
COPY --from=builder /app/target/release/worker /usr/local/bin/
COPY --from=builder /app/target/release/cli /usr/local/bin/

USER app
