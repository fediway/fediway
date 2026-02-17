
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS popular_posts AS
SELECT
    e.status_id,
    e.author_id,
    COUNT(DISTINCT e.account_id) AS engager_count,
    SUM(CASE e.type
        WHEN 0 THEN 1.0
        WHEN 1 THEN 2.0
        WHEN 2 THEN 3.0
        WHEN 5 THEN 2.0
        ELSE 0
    END) AS weighted_engagement
FROM enriched_status_engagement_events e
JOIN user_active au ON au.user_id = e.account_id
JOIN statuses s ON s.id = e.status_id
WHERE e.event_time > NOW() - INTERVAL '48 HOURS'
  AND e.type IN (0, 1, 2, 5)
  AND s.visibility = 0
  AND s.deleted_at IS NULL
GROUP BY e.status_id, e.author_id
HAVING COUNT(DISTINCT e.account_id) >= 3;

CREATE INDEX IF NOT EXISTS idx_popular_posts_weighted_engagement
    ON popular_posts(weighted_engagement DESC);

-- :down

DROP INDEX IF EXISTS idx_popular_posts_weighted_engagement;

DROP MATERIALIZED VIEW IF EXISTS popular_posts CASCADE;
