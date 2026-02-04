
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_inferred_affinity AS
SELECT
    f.account_id AS user_id,
    f.target_account_id AS author_id,
    SUM(sim.similarity * other.raw_affinity) / NULLIF(SUM(sim.similarity), 0) AS inferred_affinity,
    COUNT(*) AS contributing_users
FROM follows f
JOIN user_top_similar sim ON sim.user_id = f.account_id
JOIN user_author_affinity other
    ON other.user_id = sim.similar_user_id
    AND other.author_id = f.target_account_id
WHERE NOT EXISTS (
    SELECT 1 FROM user_author_affinity direct
    WHERE direct.user_id = f.account_id
    AND direct.author_id = f.target_account_id
)
GROUP BY f.account_id, f.target_account_id
HAVING COUNT(*) >= 2;

CREATE INDEX IF NOT EXISTS idx_user_inferred_affinity_user_id
    ON user_inferred_affinity(user_id);

CREATE INDEX IF NOT EXISTS idx_user_inferred_affinity_lookup
    ON user_inferred_affinity(user_id, author_id);

-- :down

DROP INDEX IF EXISTS idx_user_inferred_affinity_lookup;
DROP INDEX IF EXISTS idx_user_inferred_affinity_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_inferred_affinity CASCADE;
