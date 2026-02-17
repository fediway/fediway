
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS second_degree_candidates AS
SELECT
    sd.user_id,
    sd.author_id,
    sd.followed_by_count,
    a.username,
    a.domain,
    COALESCE(ast.followers_count, 0) AS followers_count,
    COALESCE(ast.statuses_count, 0) AS statuses_count
FROM second_degree_follow_counts sd
JOIN accounts a ON a.id = sd.author_id
LEFT JOIN account_stats ast ON ast.account_id = sd.author_id
WHERE NOT EXISTS (
    SELECT 1 FROM follows f
    WHERE f.account_id = sd.user_id
    AND f.target_account_id = sd.author_id
)
AND a.suspended_at IS NULL
AND a.silenced_at IS NULL
AND EXISTS (
    SELECT 1 FROM statuses s
    WHERE s.account_id = sd.author_id
    AND s.created_at > NOW() - INTERVAL '7 DAYS'
);

CREATE INDEX IF NOT EXISTS idx_second_degree_candidates_user_id
    ON second_degree_candidates(user_id);

CREATE INDEX IF NOT EXISTS idx_second_degree_candidates_author_id
    ON second_degree_candidates(author_id);

-- :down

DROP INDEX IF EXISTS idx_second_degree_candidates_author_id;
DROP INDEX IF EXISTS idx_second_degree_candidates_user_id;

DROP MATERIALIZED VIEW IF EXISTS second_degree_candidates CASCADE;
