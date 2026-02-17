
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_followed_affinity AS
SELECT
    f.account_id AS user_id,
    f.target_account_id AS author_id,
    COALESCE(direct.raw_affinity, 0) AS direct_affinity,
    COALESCE(inferred.inferred_affinity, 0) AS inferred_affinity,
    CASE
        WHEN direct.raw_affinity IS NOT NULL THEN direct.raw_affinity
        WHEN inferred.inferred_affinity IS NOT NULL THEN inferred.inferred_affinity * 0.7
        ELSE 0
    END AS effective_affinity,
    CASE
        WHEN direct.raw_affinity IS NOT NULL THEN 'direct'
        WHEN inferred.inferred_affinity IS NOT NULL THEN 'inferred'
        ELSE 'none'
    END AS affinity_source
FROM follows f
LEFT JOIN user_author_affinity direct
    ON direct.user_id = f.account_id
    AND direct.author_id = f.target_account_id
LEFT JOIN user_inferred_affinity inferred
    ON inferred.user_id = f.account_id
    AND inferred.author_id = f.target_account_id;

CREATE INDEX IF NOT EXISTS idx_user_followed_affinity_user_id
    ON user_followed_affinity(user_id);

CREATE INDEX IF NOT EXISTS idx_user_followed_affinity_lookup
    ON user_followed_affinity(user_id, author_id);

-- :down

DROP INDEX IF EXISTS idx_user_followed_affinity_lookup;
DROP INDEX IF EXISTS idx_user_followed_affinity_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_followed_affinity CASCADE;
