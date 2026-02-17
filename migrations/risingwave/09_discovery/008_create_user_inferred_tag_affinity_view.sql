
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_inferred_tag_affinity AS
SELECT
    f.account_id AS user_id,
    apt.tag_id,
    apt.tag_name,
    SUM(apt.usage_count) AS total_usage,
    COUNT(DISTINCT apt.author_id) AS contributing_accounts,
    AVG(apt.usage_count) AS avg_usage
FROM follows f
JOIN local_accounts la ON la.account_id = f.account_id
JOIN author_primary_tags apt ON apt.author_id = f.target_account_id
WHERE NOT EXISTS (
    SELECT 1 FROM user_tag_affinity uta
    WHERE uta.user_id = f.account_id
    AND uta.tag_id = apt.tag_id
)
GROUP BY f.account_id, apt.tag_id, apt.tag_name
HAVING COUNT(DISTINCT apt.author_id) >= 2;

CREATE INDEX IF NOT EXISTS idx_user_inferred_tag_affinity_user_id
    ON user_inferred_tag_affinity(user_id);

-- :down

DROP INDEX IF EXISTS idx_user_inferred_tag_affinity_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_inferred_tag_affinity CASCADE;
