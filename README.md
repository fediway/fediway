# Fediway Feeds

Fediway brings algorithmic feeds to Mastodon in an attempt to make the Fediverse more attractive to new users. Fediway feeds can be integrated into an existing mastodon server by simply redirecting desired endpoints such as `timelines/home` via nginx to the fediway server.

## Table Of Contents

- [The Algorithm](#how_it_works)
    - [Recommendation Engine](#engine)
    - [Candidate Sources](#sources)

<a name="how_it_works"></a>

## How it works?

The algorithm follows of a multi-stage pipeline that consists of the following main stages:

1. **Candidate Sourcing**: ~1000 Statuses are fetched from various sources which aims to preselect the best candidates from millions of statuses.
2. **Ranking**: These candidates are ranked by a machine learning model that estimates the likelihood of user interaction with each candidate.
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