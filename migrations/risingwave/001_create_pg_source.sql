
-- :up

CREATE SOURCE IF NOT EXISTS pg_source WITH (
    connector = 'postgres-cdc',
    hostname = '{{ db_host }}',
    port = '{{ db_port }}',
    username = '{{ db_user }}',
    password = '{{ db_pass }}',
    database.name = '{{ db_name }}',
    schema.name = 'public',
    publication.name = 'risingwave',
    slot.name = 'risingwave_slot',
    debezium.snapshot.delay.ms = '5000' -- create snapshot every 5 seconds
);

-- :down

DROP SOURCE IF EXISTS pg_source;