-- :up
CREATE MATERIALIZED VIEW status_engagements AS
(
  -- favourites
  SELECT
    f.account_id,
    f.status_id,
    s.account_id as author_id,
    'favourite' AS type,
    f.created_at AS event_time,
    s.created_at AS status_event_time
  FROM favourites f
  JOIN statuses s ON s.id = f.status_id

  UNION ALL

  -- reblogs
  SELECT
    s.account_id,
    s.reblog_of_id AS status_id,
    s1.account_id as author_id,
    'reblog' AS type,
    s.created_at AS event_time,
    s1.created_at AS status_event_time
  FROM statuses s
  JOIN statuses s1 ON s.reblog_of_id = s1.id
  WHERE s.reblog_of_id IS NOT NULL

  UNION ALL

  -- replies
  SELECT
    s.account_id,
    s.in_reply_to_id AS status_id,
    s1.account_id as author_id,
    'reply' AS type,
    s.created_at AS event_time,
    s1.created_at AS status_event_time
  FROM statuses s
  JOIN statuses s1 ON s.in_reply_to_id = s1.id
  WHERE s.in_reply_to_id IS NOT NULL 
);

-- :down
DROP VIEW IF EXISTS status_engagements;