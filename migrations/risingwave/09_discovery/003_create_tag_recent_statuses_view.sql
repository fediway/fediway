
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS tag_recent_statuses AS
SELECT
    st.tag_id,
    s.id AS status_id,
    s.account_id AS author_id,
    s.created_at,
    s.language
FROM statuses s
JOIN statuses_tags st ON st.status_id = s.id
WHERE s.created_at > NOW() - INTERVAL '48 HOURS'
  AND s.visibility = 0
  AND s.reblog_of_id IS NULL
  AND s.in_reply_to_id IS NULL
  AND s.deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_tag_recent_statuses_tag_id
    ON tag_recent_statuses(tag_id);

CREATE INDEX IF NOT EXISTS idx_tag_recent_statuses_created_at
    ON tag_recent_statuses(created_at DESC);

-- :down

DROP INDEX IF EXISTS idx_tag_recent_statuses_created_at;
DROP INDEX IF EXISTS idx_tag_recent_statuses_tag_id;

DROP MATERIALIZED VIEW IF EXISTS tag_recent_statuses CASCADE;
