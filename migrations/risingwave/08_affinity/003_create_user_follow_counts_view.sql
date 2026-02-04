
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_follow_counts AS
SELECT account_id, COUNT(*) AS follow_count
FROM follows
GROUP BY account_id;

CREATE INDEX IF NOT EXISTS idx_user_follow_counts_account_id
    ON user_follow_counts(account_id);

-- :down

DROP INDEX IF EXISTS idx_user_follow_counts_account_id;

DROP MATERIALIZED VIEW IF EXISTS user_follow_counts CASCADE;
