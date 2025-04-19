-- :up
CREATE MATERIALIZED VIEW status_engagements AS
(
  -- favourites
  SELECT
    f.account_id,
    f.status_id,
    'favourite' AS type,
    f.created_at AS event_time
  FROM favourites f

  UNION ALL

  -- reblogs
  SELECT
    s.account_id,
    s.reblog_of_id AS status_id,
    'reblog' AS type,
    s.created_at AS event_time
  FROM statuses s
  WHERE s.reblog_of_id IS NOT NULL

  UNION ALL

  -- replies
  SELECT
    s.account_id,
    s.in_reply_to_id AS status_id,
    'reply' AS type,
    s.created_at AS event_time
  FROM statuses s
  WHERE s.in_reply_to_id IS NOT NULL 
);

-- :down
DROP VIEW IF EXISTS status_engagements;