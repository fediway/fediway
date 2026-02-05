
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_tag_affinity AS
SELECT
    e.account_id AS user_id,
    st.tag_id,
    t.name AS tag_name,
    COUNT(*) AS engagement_count,
    COUNT(*) FILTER (WHERE e.type = 0) AS num_favs,
    COUNT(*) FILTER (WHERE e.type = 1) AS num_reblogs,
    COUNT(*) FILTER (WHERE e.type = 2) AS num_replies,
    COUNT(*) FILTER (WHERE e.type = 5) AS num_quotes,
    (
        COUNT(*) FILTER (WHERE e.type = 0) * 1.0 +
        COUNT(*) FILTER (WHERE e.type = 1) * 2.0 +
        COUNT(*) FILTER (WHERE e.type = 2) * 3.0 +
        COUNT(*) FILTER (WHERE e.type = 5) * 2.0
    ) AS raw_affinity,
    MAX(e.event_time) AS last_engaged_at
FROM enriched_status_engagement_events e
JOIN statuses_tags st ON st.status_id = e.status_id
JOIN tags t ON t.id = st.tag_id
WHERE e.event_time > NOW() - INTERVAL '60 DAYS'
GROUP BY e.account_id, st.tag_id, t.name
HAVING COUNT(*) >= 2;

CREATE INDEX IF NOT EXISTS idx_user_tag_affinity_user_id
    ON user_tag_affinity(user_id);

CREATE INDEX IF NOT EXISTS idx_user_tag_affinity_tag_id
    ON user_tag_affinity(tag_id);

-- :down

DROP INDEX IF EXISTS idx_user_tag_affinity_tag_id;
DROP INDEX IF EXISTS idx_user_tag_affinity_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_tag_affinity CASCADE;
