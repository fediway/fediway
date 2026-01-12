# Stage 1: Build the application
FROM rust:1.92-slim-trixie AS builder

# Install required system dependencies
RUN apt-get update && \
    apt-get install -y build-essential pkg-config libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Create app directory and set as workdir
WORKDIR /app

# Copy actual source code
COPY . .

# Build
RUN cargo build --release

# Stage 2: Create minimal runtime image
FROM debian:trixie-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy built binary from builder stage
COPY --from=builder /app/target/release/orbit /usr/local/bin/

# Set the entry point to run your application
ENTRYPOINT ["orbit"]