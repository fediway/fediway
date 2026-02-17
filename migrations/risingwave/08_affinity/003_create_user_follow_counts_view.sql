
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_follow_counts AS
SELECT account_id AS user_id, COUNT(*) AS follow_count
FROM follows
GROUP BY account_id;

CREATE INDEX IF NOT EXISTS idx_user_follow_counts_user_id
    ON user_follow_counts(user_id);

-- :down

DROP INDEX IF EXISTS idx_user_follow_counts_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_follow_counts CASCADE;
