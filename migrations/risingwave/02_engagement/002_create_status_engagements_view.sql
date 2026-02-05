-- :up

CREATE TABLE IF NOT EXISTS status_engagements (
  account_id BIGINT,
  status_id BIGINT,
  type INT,
  entity_id BIGINT,
  event_time TIMESTAMP,
  PRIMARY KEY (account_id, status_id, type)
) APPEND ONLY ON CONFLICT IGNORE;

CREATE SINK IF NOT EXISTS status_engagements_favourites_sink
INTO status_engagements AS
SELECT
  f.account_id,
  f.status_id,
  0 AS type,
  f.id as entity_id,
  f.created_at AS event_time
FROM favourites f
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS status_engagements_reblogs_sink
INTO status_engagements AS
SELECT
  s.account_id,
  s.reblog_of_id AS status_id,
  1 AS type,
  s.id as entity_id,
  s.created_at AS event_time
FROM statuses s
WHERE s.reblog_of_id IS NOT NULL
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS status_engagements_replies_sink
INTO status_engagements AS
SELECT
  s.account_id,
  s.in_reply_to_id AS status_id,
  2 AS type,
  s.id as entity_id,
  s.created_at AS event_time
FROM statuses s
WHERE s.in_reply_to_id IS NOT NULL
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS status_engagements_poll_votes_sink
INTO status_engagements AS
SELECT
  v.account_id,
  p.status_id,
  3 AS type,
  v.id as entity_id,
  v.created_at AS event_time
FROM poll_votes v
JOIN polls p ON p.id = v.poll_id
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS status_engagements_bookmarks_sink
INTO status_engagements AS
SELECT
  account_id,
  status_id,
  4 AS type,
  id as entity_id,
  created_at AS event_time
FROM bookmarks
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS status_engagements_quotes_sink
INTO status_engagements AS
SELECT
  account_id,
  quoted_status_id,
  5 AS type,
  status_id as entity_id,
  created_at AS event_time
FROM quotes
WHERE state = 1
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

-- :down

DROP SINK IF EXISTS status_engagements_quotes_sink;
DROP SINK IF EXISTS status_engagements_bookmarks_sink;
DROP SINK IF EXISTS status_engagements_poll_votes_sink;
DROP SINK IF EXISTS status_engagements_replies_sink;
DROP SINK IF EXISTS status_engagements_reblogs_sink;
DROP SINK IF EXISTS status_engagements_favourites_sink;

DROP VIEW IF EXISTS status_engagements;
