# Fediway Feeds

Fediway brings algorithmic feeds to Mastodon in an attempt to make the Fediverse more attractive to new users. Fediway feeds can be integrated into an existing mastodon server by simply redirecting desired endpoints such as `timelines/home` via nginx to the fediway server.

## Table Of Contents

- [The Algorithm](#how_it_works)
    - [Recommendation Engine](#engine)
    - [Candidate Sources](#sources)
- [Setup](#setup)

<a name="how_it_works"></a>

## How it works?

The algorithm follows of a multi-stage pipeline that consists of the following main stages:

1. **Candidate Sourcing**: ~1000 Posts are fetched from various sources which aims to preselect the best candidates from millions of statuses.
2. **Ranking**: The candidates are ranked by a machine learning model that estimates the likelihood of user interaction with each candidate.
3. **Sampling**: In the final stage, heuristics are applied to diversify recommendations which are sampled depending on the engagement scores estimated in the ranking step.

<a name="engine"></a>

### Recommendation Engine

The project includes a recommendation engine that makes it easy to build custom recommendation pipelines:

```py
from modules.fediway.feed import Feed
from modules.fediway.rankers import SimpleStatsRanker
from modules.fediway.sources import (
    MostInteractedByMutualFollowsSource,
    CollaborativeFilteringSource,
)

pipeline = (
    Feed()
    .select('status_id')
    .source(MostInteractedByMutualFollowsSource(account_id), 100)
    .source(CollaborativeFilteringSource(account_id, language='en'), 100)
    .rank(SimpleStatsRanker())
    .diversify(by='status:account_id', penalty=0.1)
    .sample(20, unique=True)
    .paginate(20, offset=0)
)

status_ids = pipeline.execute()
```

<a name="sources"></a>

### Candidate Sources

Narrowing down the vast pool consiting of up to billions of potential posts to recommend is a critical step in finding posts that users are actually interested in. 

<a name="setup"></a>

## Setup

A minimal working fediway server requires the following services:

- [Memgraph](https://memgraph.com/) - In memory graph database for candidate sourcing
- [RisingWave](https://risingwave.com/) - Streaming database serving real time feature for ML inference
- [Apache Kafka](https://kafka.apache.org/) - Message broker for ingesting data into memgraph, serving real time features and more

```sh
version: '3.8'

services:
  memgraph:
    image: memgraph/memgraph-mage:3.1.1-memgraph-3.1.1
    ports:
      - "7687:7687"

  postgres:
    image: postgres:16
    shm_size: 256mb
    environment:
      - POSTGRES_USER=mastodon
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=mastodon_development
    command: 
      - "postgres"
      - "-c"
      - "wal_level=logical"
    volumes:
      - ./../postgres16:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - app_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mastodon -d mastodon_development"]
      interval: 5s
      timeout: 5s
      retries: 5

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    networks:
      - app_network

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:29092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
    ports:
      - "9092:9092"
      - "29092:29092"
    networks:
      - app_network

  risingwave:
    image: risingwavelabs/risingwave:latest
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "4566:4566"
      - "5691:5691"
    networks:
      - app_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5691/metrics"]
      interval: 5s
      timeout: 5s
      retries: 5

networks:
  app_network:
    driver: bridge
```

### Risingwave

## Api

Start server

```sh
uvicorn apps.api.main:app --reload
```

## Kafka Consumer

```sh
faststream run apps.streaming.main:app
```

## Job Scheduling

Start task beat scheduler

```sh
celery -A apps.worker.main beat --loglevel=info
```

Start task worker scheduler

```sh
celery -A apps.worker.main worker --loglevel=info
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