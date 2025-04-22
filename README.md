# Fediway Feeds

## Api

Start server

```sh
uvicorn app.main:app --reload
```

## Kafka Consumer

```sh
faststream run app.pipeline:app --workers 4
```

## Job Scheduling

Start task beat scheduler

```sh
celery -A app.worker beat --loglevel=info
```

Start task worker scheduler

```sh
celery -A app.worker worker --loglevel=info
```

<!-- Start worker to process topics
```sh
celery -A jobs.main worker --queues=topics --loglevel=info
``` 
-->

## Setup

### RisingWave

Create a new postgres user with CDC privileges.

```sql
-- psql -U postgres

-- Grand CDC privileges
CREATE USER risingwave REPLICATION LOGIN CREATEDB;
ALTER USER risingwave WITH PASSWORD 'password';
GRANT CONNECT ON DATABASE mastodon_development TO risingwave;
GRANT USAGE ON SCHEMA public TO risingwave;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO risingwave;
GRANT CREATE ON DATABASE mastodon_development TO risingwave;
```

### Postgres

Run migrations:

```sh
alembic upgrade head
```

Refresh migrations

```sh
alembic downgrade base
```

Create migration

```sh
alembic revision -m "create topics table"
```

### Feast

Storing registry on s3:

```sh
# 1. install requirements
python -m pip install feast[aws]

# 1. add variable to .env file
FEAST_REGISTRY=s3://my-bucket/registry.db

# 2. export the following variables
export FEAST_S3_ENDPOINT_URL="https://fsn1.your-objectstorage.com"
export AWS_ACCESS_KEY_ID="YOUR_S3_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="YOUR_S3_SECRET_KEY"
```

## ip2location

Download ip-database

```sh
curl -o data/geo-whois-asn-country-ipv4.mmdb https://cdn.jsdelivr.net/npm/@ip-location-db/geo-whois-asn-country-mmdb/geo-whois-asn-country-ipv4.mmdb
curl -o data/geo-whois-asn-country-ipv6.mmdb https://cdn.jsdelivr.net/npm/@ip-location-db/geo-whois-asn-country-mmdb/geo-whois-asn-country-ipv6.mmdb
```

## ActivityPub

https://w3c.github.io/activitypub