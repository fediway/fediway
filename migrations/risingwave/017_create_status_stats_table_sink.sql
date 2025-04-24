
-- :up
CREATE SINK IF NOT EXISTS status_stats_sink
FROM status_stats
WITH (
    connector='kafka',
    properties.bootstrap.server='${bootstrap_server}',
    topic='status_stats',
    primary_key='id',
) FORMAT DEBEZIUM ENCODE JSON;

-- :down
DROP SINK IF EXISTS status_stats_sink;