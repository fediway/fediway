-- :up
CREATE TABLE IF NOT EXISTS status_engagement_events (
  account_id BIGINT,
  status_id BIGINT,
  type VARCHAR,
  favourite_id BIGINT,
  reblog_id BIGINT,
  reply_id BIGINT,
  event_time TIMESTAMP,
  WATERMARK FOR event_time AS event_time - INTERVAL '5 seconds'
) APPEND ONLY;

CREATE MATERIALIZED VIEW IF NOT EXISTS status_engagements AS
(
  -- favourites
  SELECT
    f.account_id,
    f.status_id,
    'favourite' AS type,
    f.id as favourite_id,
    NULL::BIGINT as reblog_id,
    NULL::BIGINT as reply_id,
    f.created_at AS event_time
  FROM favourites f

  UNION ALL

  -- reblogs
  SELECT
    s.account_id,
    s.reblog_of_id AS status_id,
    'reblog' AS type,
    NULL::BIGINT as favourite_id,
    s.id as reblog_id,
    NULL::BIGINT as reply_id,
    s.created_at AS event_time
  FROM statuses s
  WHERE s.reblog_of_id IS NOT NULL

  UNION ALL

  -- replies
  SELECT
    s.account_id,
    s.in_reply_to_id AS status_id,
    'reply' AS type,
    NULL::BIGINT as favourite_id,
    NULL::BIGINT as reblog_id,
    s.id as reply_id,
    s.created_at AS event_time
  FROM statuses s
  WHERE s.in_reply_to_id IS NOT NULL 
);

CREATE SINK IF NOT EXISTS status_engagements_sink
INTO status_engagement_events
FROM status_engagements
WITH (type = 'append-only', force_append_only='true');

-- :down
DROP VIEW IF EXISTS status_engagements;
DROP TABLE IF EXISTS status_engagement_events CASCADE;
DROP SINK IF EXISTS status_engagements_sink;