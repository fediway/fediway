
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_follow_overlap AS
SELECT
    f1.account_id AS user_a,
    f2.account_id AS user_b,
    COUNT(*) AS shared_follows
FROM follows f1
JOIN follows f2
    ON f1.target_account_id = f2.target_account_id
    AND f1.account_id < f2.account_id
JOIN user_active a1 ON a1.user_id = f1.account_id
JOIN user_active a2 ON a2.user_id = f2.account_id
GROUP BY f1.account_id, f2.account_id
HAVING COUNT(*) >= 5;

CREATE INDEX IF NOT EXISTS idx_user_follow_overlap_user_a
    ON user_follow_overlap(user_a);

CREATE INDEX IF NOT EXISTS idx_user_follow_overlap_user_b
    ON user_follow_overlap(user_b);

-- :down

DROP INDEX IF EXISTS idx_user_follow_overlap_user_b;
DROP INDEX IF EXISTS idx_user_follow_overlap_user_a;

DROP MATERIALIZED VIEW IF EXISTS user_follow_overlap CASCADE;
