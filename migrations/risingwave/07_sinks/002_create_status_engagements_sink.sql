
-- :up

CREATE SINK IF NOT EXISTS status_engagements_sink AS
SELECT *
FROM enriched_status_engagement_events
WHERE event_time > NOW() - INTERVAL '3 DAYS'
WITH (
  connector='kafka',
  properties.bootstrap.server='{{ bootstrap_server }}',
  topic='status_engagements',
  primary_key='account_id,status_id,type',
) FORMAT PLAIN ENCODE JSON (
  force_append_only='true'
);

-- :down

DROP SINK IF EXISTS status_engagements_sink;
