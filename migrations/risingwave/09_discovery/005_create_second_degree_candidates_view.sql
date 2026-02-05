
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS second_degree_candidates AS
SELECT
    sd.user_id,
    sd.suggested_account_id,
    sd.followed_by_count,
    a.username,
    a.domain,
    a.followers_count,
    a.statuses_count
FROM second_degree_follow_counts sd
JOIN accounts a ON a.id = sd.suggested_account_id
WHERE NOT EXISTS (
    SELECT 1 FROM follows f
    WHERE f.account_id = sd.user_id
    AND f.target_account_id = sd.suggested_account_id
)
AND a.suspended_at IS NULL
AND a.silenced_at IS NULL
AND EXISTS (
    SELECT 1 FROM statuses s
    WHERE s.account_id = sd.suggested_account_id
    AND s.created_at > NOW() - INTERVAL '7 DAYS'
);

CREATE INDEX IF NOT EXISTS idx_second_degree_candidates_user_id
    ON second_degree_candidates(user_id);

CREATE INDEX IF NOT EXISTS idx_second_degree_candidates_suggested
    ON second_degree_candidates(suggested_account_id);

-- :down

DROP INDEX IF EXISTS idx_second_degree_candidates_suggested;
DROP INDEX IF EXISTS idx_second_degree_candidates_user_id;

DROP MATERIALIZED VIEW IF EXISTS second_degree_candidates CASCADE;
