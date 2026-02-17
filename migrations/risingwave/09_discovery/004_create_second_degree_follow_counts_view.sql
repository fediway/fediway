
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS second_degree_follow_counts AS
SELECT
    f1.account_id AS user_id,
    f2.target_account_id AS author_id,
    COUNT(*) AS followed_by_count
FROM follows f1
JOIN local_accounts la ON la.account_id = f1.account_id
JOIN follows f2 ON f2.account_id = f1.target_account_id
WHERE f1.account_id != f2.target_account_id
GROUP BY f1.account_id, f2.target_account_id
HAVING COUNT(*) >= 3;

CREATE INDEX IF NOT EXISTS idx_second_degree_follow_counts_user_id
    ON second_degree_follow_counts(user_id);

CREATE INDEX IF NOT EXISTS idx_second_degree_follow_counts_author_id
    ON second_degree_follow_counts(author_id);

-- :down

DROP INDEX IF EXISTS idx_second_degree_follow_counts_author_id;
DROP INDEX IF EXISTS idx_second_degree_follow_counts_user_id;

DROP MATERIALIZED VIEW IF EXISTS second_degree_follow_counts CASCADE;
