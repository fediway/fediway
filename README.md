# Fediway Feeds

## Api

Start server

```sh
uvicorn app.main:app --reload
```

## Kafka Consumer

```sh
faststream run app.consumer:app
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
``` -->

## DB

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

## ip2location

Download ip-database

```sh
curl -o data/geo-whois-asn-country-ipv4.mmdb https://cdn.jsdelivr.net/npm/@ip-location-db/geo-whois-asn-country-mmdb/geo-whois-asn-country-ipv4.mmdb
curl -o data/geo-whois-asn-country-ipv6.mmdb https://cdn.jsdelivr.net/npm/@ip-location-db/geo-whois-asn-country-mmdb/geo-whois-asn-country-ipv6.mmdb
```

## ActivityPub

https://w3c.github.io/activitypub