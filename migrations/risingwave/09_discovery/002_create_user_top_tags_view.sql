
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_top_tags AS
SELECT user_id, tag_id, tag_name, raw_affinity FROM (
    SELECT
        uta.user_id,
        uta.tag_id,
        uta.tag_name,
        uta.raw_affinity,
        ROW_NUMBER() OVER (PARTITION BY uta.user_id ORDER BY uta.raw_affinity DESC) AS rank
    FROM user_tag_affinity uta
    JOIN local_accounts la ON la.account_id = uta.user_id
) ranked
WHERE rank <= 50;

CREATE INDEX IF NOT EXISTS idx_user_top_tags_user_id
    ON user_top_tags(user_id);

-- :down

DROP INDEX IF EXISTS idx_user_top_tags_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_top_tags CASCADE;
