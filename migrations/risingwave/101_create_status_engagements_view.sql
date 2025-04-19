-- :up
CREATE VIEW status_engagements AS
WITH engagements AS (
  -- 1) all favourites
  SELECT
    f.account_id,
    f.status_id,
    TRUE  AS is_favourited,
    FALSE AS is_reblogged,
    FALSE AS is_replied
  FROM favourites f

  UNION ALL

  -- 2) all reblogs
  SELECT
    s.account_id,
    s.reblog_of_id AS status_id,
    FALSE AS is_favourited,
    TRUE  AS is_reblogged,
    FALSE AS is_replied
  FROM statuses s
  WHERE s.reblog_of_id IS NOT NULL

  UNION ALL

  -- 3) all replies
  SELECT
    s.account_id,
    s.in_reply_to_id AS status_id,
    FALSE AS is_favourited,
    FALSE AS is_reblogged,
    TRUE  AS is_replied
  FROM statuses s
  WHERE s.in_reply_to_id IS NOT NULL
),
aggregated AS (
  -- roll up multiple engagement‐rows per (account_id, status_id)
  SELECT
    account_id,
    status_id,
    bool_or(is_favourited) AS is_favourited,
    bool_or(is_reblogged) AS is_reblogged,
    bool_or(is_replied)   AS is_replied
  FROM engagements
  GROUP BY account_id, status_id
)
SELECT
  a.account_id,
  a.status_id,
  s.account_id AS author_id,
  a.is_favourited,
  a.is_reblogged,
  a.is_replied
FROM aggregated a
-- join back to statuses to fetch the author_id
JOIN statuses s
  ON s.id = a.status_id;

-- :down
DROP VIEW IF EXISTS status_engagements;