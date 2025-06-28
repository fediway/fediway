# Stage 1: Build the application
FROM rust:1.86-slim-bookworm AS builder

# Create app directory and set as workdir
WORKDIR /app

# Copy actual source code
COPY . .

# Build
RUN cargo build --release

# Stage 2: Create minimal runtime image
FROM debian:bookworm-slim

# Copy built binary from builder stage
COPY --from=builder /app/target/release/orbit /usr/local/bin/

# Set the entry point to run your application
ENTRYPOINT ["orbit"]