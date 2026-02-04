
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_top_tags AS
SELECT user_id, tag_id, tag_name, raw_affinity FROM (
    SELECT
        user_id,
        tag_id,
        tag_name,
        raw_affinity,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY raw_affinity DESC) AS rank
    FROM user_tag_affinity
) ranked
WHERE rank <= 50;

CREATE INDEX IF NOT EXISTS idx_user_top_tags_user_id
    ON user_top_tags(user_id);

-- :down

DROP INDEX IF EXISTS idx_user_top_tags_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_top_tags CASCADE;
