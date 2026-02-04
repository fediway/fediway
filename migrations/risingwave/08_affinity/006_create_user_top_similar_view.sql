
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_top_similar AS
SELECT user_id, similar_user_id, similarity FROM (
    SELECT
        user_a AS user_id,
        user_b AS similar_user_id,
        jaccard AS similarity,
        ROW_NUMBER() OVER (PARTITION BY user_a ORDER BY jaccard DESC) AS rank
    FROM active_user_similarity
    UNION ALL
    SELECT
        user_b AS user_id,
        user_a AS similar_user_id,
        jaccard AS similarity,
        ROW_NUMBER() OVER (PARTITION BY user_b ORDER BY jaccard DESC) AS rank
    FROM active_user_similarity
) ranked
WHERE rank <= 50;

CREATE INDEX IF NOT EXISTS idx_user_top_similar_user_id
    ON user_top_similar(user_id);

CREATE INDEX IF NOT EXISTS idx_user_top_similar_similar_user_id
    ON user_top_similar(similar_user_id);

-- :down

DROP INDEX IF EXISTS idx_user_top_similar_similar_user_id;
DROP INDEX IF EXISTS idx_user_top_similar_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_top_similar CASCADE;
