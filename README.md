# Fediway Feeds

## Api

Start server

```sh
uvicorn app.main:app --reload
```

## Job Scheduling

Start scheduler worker

```sh
celery -A jobs.main worker --queues=local --loglevel=info
```

Start worker to process topics

```sh
celery -A jobs.main worker --queues=topics --loglevel=info
```

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