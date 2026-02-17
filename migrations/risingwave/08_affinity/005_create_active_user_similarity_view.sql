
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_similarity AS
SELECT
    o.user_a,
    o.user_b,
    o.shared_follows,
    o.shared_follows::FLOAT / (fc1.follow_count + fc2.follow_count - o.shared_follows) AS jaccard
FROM user_follow_overlap o
JOIN user_follow_counts fc1 ON fc1.user_id = o.user_a
JOIN user_follow_counts fc2 ON fc2.user_id = o.user_b
WHERE o.shared_follows::FLOAT / (fc1.follow_count + fc2.follow_count - o.shared_follows) >= 0.05;

CREATE INDEX IF NOT EXISTS idx_user_similarity_user_a
    ON user_similarity(user_a);

CREATE INDEX IF NOT EXISTS idx_user_similarity_user_b
    ON user_similarity(user_b);

-- :down

DROP INDEX IF EXISTS idx_user_similarity_user_b;
DROP INDEX IF EXISTS idx_user_similarity_user_a;

DROP MATERIALIZED VIEW IF EXISTS user_similarity CASCADE;
