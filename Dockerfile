FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

ENV APP_SECRET=
ENV APP_HOST=
ENV API_URL=

ENV DB_HOST=localhost
ENV DB_PORT=5432
ENV DB_USER=mastodon
ENV DB_PASS=
ENV DB_NAME=mastodon_production

ENV REDIS_HOST=localhost
ENV REDIS_PORT=6379
ENV REDIS_USER=postgres
ENV REDIS_PASS=

ENV IPV4_LOCATION_FILE=data/geo-whois-asn-country-ipv4.mmdb
ENV IPV6_LOCATION_FILE=data/geo-whois-asn-country-ipv6.mmdb

# Create non-root user and set up directories
RUN addgroup --system --gid 1001 fediway && \
    adduser --system --uid 1001 --gid 1001 --no-create-home fediway && \
    mkdir -p /app && \
    chown -R fediway:fediway /app

# Set work directory
WORKDIR /app

# Copy dependency files
COPY --chown=fediway:fediway pyproject.toml uv.lock ./

# Install PyTorch CPU-only first (smaller image)
RUN uv pip install --system --no-cache torch --index-url https://download.pytorch.org/whl/cpu

# Install dependencies (core + commonly needed extras)
# Adjust extras based on your deployment needs
RUN uv pip install --system --no-cache ".[vectors,embeddings,streaming,geo]"

# Download whois geolocation databases
ADD https://cdn.jsdelivr.net/npm/@ip-location-db/geo-whois-asn-country-mmdb/geo-whois-asn-country-ipv4.mmdb data/geo-whois-asn-country-ipv4.mmdb
ADD https://cdn.jsdelivr.net/npm/@ip-location-db/geo-whois-asn-country-mmdb/geo-whois-asn-country-ipv6.mmdb data/geo-whois-asn-country-ipv6.mmdb
RUN chown -R fediway:fediway data

# Copy application code
COPY --chown=fediway:fediway . .

# Switch to fediway user
USER fediway

# Run API
CMD ["fastapi", "run", "apps/api/main.py"]
