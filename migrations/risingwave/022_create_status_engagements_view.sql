-- :up
CREATE MATERIALIZED VIEW IF NOT EXISTS status_engagements AS
(
  -- favourites
  SELECT
    f.account_id,
    f.status_id,
    0 AS type,
    f.id as favourite_id,
    NULL::BIGINT as reblog_id,
    NULL::BIGINT as reply_id,
    NULL::BIGINT as poll_vote_id,
    NULL::BIGINT as bookmark_id,
    f.created_at AS event_time
  FROM favourites f

  UNION ALL

  -- reblogs
  SELECT
    s.account_id,
    s.reblog_of_id AS status_id,
    1 AS type,
    NULL::BIGINT as favourite_id,
    s.id as reblog_id,
    NULL::BIGINT as reply_id,
    NULL::BIGINT as poll_vote_id,
    NULL::BIGINT as bookmark_id,
    s.created_at AS event_time
  FROM statuses s
  WHERE s.reblog_of_id IS NOT NULL

  UNION ALL

  -- replies
  SELECT
    s.account_id,
    s.in_reply_to_id AS status_id,
    2 AS type,
    NULL::BIGINT as favourite_id,
    NULL::BIGINT as reblog_id,
    s.id as reply_id,
    NULL::BIGINT as poll_vote_id,
    NULL::BIGINT as bookmark_id,
    s.created_at AS event_time
  FROM statuses s
  WHERE s.in_reply_to_id IS NOT NULL 

  UNION ALL

  -- poll votes
  SELECT
    v.account_id,
    p.status_id,
    3 AS type,
    NULL::BIGINT as favourite_id,
    NULL::BIGINT as reblog_id,
    NULL::BIGINT as reply_id,
    v.id as poll_vote_id,
    NULL::BIGINT as bookmark_id,
    v.created_at AS event_time
  FROM poll_votes v
  JOIN polls p ON p.id = v.poll_id

  UNION ALL

  -- bookmarks
  SELECT
    b.account_id,
    b.status_id,
    4 AS type,
    NULL::BIGINT as favourite_id,
    NULL::BIGINT as reblog_id,
    NULL::BIGINT as reply_id,
    NULL::BIGINT as poll_vote_id,
    b.id as bookmark_id,
    b.created_at AS event_time
  FROM bookmarks b
);

-- :down
DROP VIEW IF EXISTS status_engagements;
