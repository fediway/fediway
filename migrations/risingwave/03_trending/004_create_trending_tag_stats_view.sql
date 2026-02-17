
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS trending_tag_stats AS
SELECT
    st.tag_id,
    s.language,
    COUNT(DISTINCT st.status_id) AS post_count,
    COUNT(DISTINCT s.account_id) AS account_count,
    MAX(s.created_at) AS last_used
FROM statuses_tags st
JOIN statuses s ON s.id = st.status_id
WHERE s.created_at > NOW() - INTERVAL '48 HOURS'
  AND s.deleted_at IS NULL
  AND s.visibility IN (0, 1)
  AND s.language IS NOT NULL
GROUP BY st.tag_id, s.language;

CREATE INDEX IF NOT EXISTS idx_trending_tag_stats_tag_id
    ON trending_tag_stats(tag_id);

CREATE INDEX IF NOT EXISTS idx_trending_tag_stats_language
    ON trending_tag_stats(language);

-- :down

DROP INDEX IF EXISTS idx_trending_tag_stats_language;
DROP INDEX IF EXISTS idx_trending_tag_stats_tag_id;

DROP MATERIALIZED VIEW IF EXISTS trending_tag_stats CASCADE;
