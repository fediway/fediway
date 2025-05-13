-- :up
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

-- :down
DROP VIEW IF EXISTS status_engagements;