
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS recent_original_statuses AS
SELECT
    s.id AS status_id,
    s.account_id AS author_id,
    s.language,
    s.created_at
FROM statuses s
WHERE s.created_at > NOW() - INTERVAL '24 HOURS'
  AND s.visibility = 0
  AND s.reblog_of_id IS NULL
  AND s.in_reply_to_id IS NULL
  AND s.deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_recent_original_statuses_status_id
    ON recent_original_statuses(status_id);

-- :down

DROP INDEX IF EXISTS idx_recent_original_statuses_status_id;

DROP MATERIALIZED VIEW IF EXISTS recent_original_statuses CASCADE;
