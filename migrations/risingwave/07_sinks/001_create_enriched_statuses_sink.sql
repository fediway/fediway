
-- :up

CREATE SINK IF NOT EXISTS enriched_statuses_sink AS
SELECT
  *,
  created_at as event_time
FROM enriched_statuses
WHERE created_at > NOW() - INTERVAL '30 DAYS'
WITH (
  connector='kafka',
  properties.bootstrap.server='{{ bootstrap_server }}',
  topic='statuses',
  primary_key='status_id',
  properties.linger.ms='1000',
) FORMAT DEBEZIUM ENCODE JSON;

-- :down

DROP SINK IF EXISTS enriched_statuses_sink;
