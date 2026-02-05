
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS account_primary_tags AS
SELECT account_id, tag_id, tag_name, usage_count FROM (
    SELECT
        s.account_id,
        st.tag_id,
        t.name AS tag_name,
        COUNT(*) AS usage_count,
        ROW_NUMBER() OVER (PARTITION BY s.account_id ORDER BY COUNT(*) DESC) AS rank
    FROM statuses s
    JOIN statuses_tags st ON st.status_id = s.id
    JOIN tags t ON t.id = st.tag_id
    WHERE s.created_at > NOW() - INTERVAL '90 DAYS'
      AND s.deleted_at IS NULL
    GROUP BY s.account_id, st.tag_id, t.name
    HAVING COUNT(*) >= 3
) ranked
WHERE rank <= 5;

CREATE INDEX IF NOT EXISTS idx_account_primary_tags_account_id
    ON account_primary_tags(account_id);

CREATE INDEX IF NOT EXISTS idx_account_primary_tags_tag_id
    ON account_primary_tags(tag_id);

-- :down

DROP INDEX IF EXISTS idx_account_primary_tags_tag_id;
DROP INDEX IF EXISTS idx_account_primary_tags_account_id;

DROP MATERIALIZED VIEW IF EXISTS account_primary_tags CASCADE;
