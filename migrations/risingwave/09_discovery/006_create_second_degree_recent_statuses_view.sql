
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS second_degree_recent_statuses AS
SELECT
    sd.user_id,
    s.id AS status_id,
    s.account_id AS author_id,
    sd.followed_by_count,
    s.created_at,
    s.language
FROM second_degree_candidates sd
JOIN statuses s ON s.account_id = sd.author_id
WHERE s.created_at > NOW() - INTERVAL '48 HOURS'
  AND s.visibility = 0
  AND s.reblog_of_id IS NULL
  AND s.in_reply_to_id IS NULL
  AND s.deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_second_degree_recent_statuses_user_id
    ON second_degree_recent_statuses(user_id);

CREATE INDEX IF NOT EXISTS idx_second_degree_recent_statuses_lookup
    ON second_degree_recent_statuses(user_id, followed_by_count DESC);

-- :down

DROP INDEX IF EXISTS idx_second_degree_recent_statuses_lookup;
DROP INDEX IF EXISTS idx_second_degree_recent_statuses_user_id;

DROP MATERIALIZED VIEW IF EXISTS second_degree_recent_statuses CASCADE;
