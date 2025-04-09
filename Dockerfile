
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_ENV=production

ENV APP_SECRET=
ENV APP_HOST=

ENV DB_HOST=localhost
ENV DB_PORT=5432
ENV DB_USER=mastodon
ENV DB_PASS=
ENV DB_NAME=mastodon_production

ENV IPV4_LOCATION_FILE=data/geo-whois-asn-country-ipv4.mmdb
ENV IPV6_LOCATION_FILE=data/geo-whois-asn-country-ipv6.mmdb

# Create non-root user and set up directories
RUN addgroup --system --gid 1001 crawler && \
    adduser --system --uid 1001 --gid 1001 --no-create-home crawler && \
    mkdir -p /app && \
    chown -R crawler:crawler /app

# Set work directory
WORKDIR /app

# copy requirements.txt
COPY --chown=crawler:crawler requirements.txt .

# install requirements
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application code
COPY --chown=crawler:crawler . .

# Switch to crawler user
USER crawler

# run api
CMD ["fastapi", "run", "api/main.py"]