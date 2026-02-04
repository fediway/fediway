
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS status_engagement_counts AS
SELECT
    e.status_id,
    COUNT(*) FILTER (WHERE e.type = 0) AS num_favs,
    COUNT(*) FILTER (WHERE e.type = 1) AS num_reblogs,
    COUNT(*) FILTER (WHERE e.type = 2) AS num_replies,
    COUNT(*) FILTER (WHERE e.type = 5) AS num_quotes,
    COUNT(DISTINCT e.account_id) AS unique_engagers,
    COUNT(DISTINCT a.domain) AS unique_domains,
    (
        COUNT(*) FILTER (WHERE e.type = 0) * 1.0 +
        COUNT(*) FILTER (WHERE e.type = 1) * 2.0 +
        COUNT(*) FILTER (WHERE e.type = 2) * 3.0 +
        COUNT(*) FILTER (WHERE e.type = 5) * 2.0
    ) AS weighted_engagement,
    MIN(e.event_time) AS first_engagement_at,
    MAX(e.event_time) AS last_engagement_at
FROM status_engagements e
JOIN accounts a ON a.id = e.account_id
WHERE e.event_time > NOW() - INTERVAL '24 HOURS'
GROUP BY e.status_id
HAVING COUNT(DISTINCT e.account_id) >= 3;

CREATE INDEX IF NOT EXISTS idx_status_engagement_counts_status_id
    ON status_engagement_counts(status_id);

-- :down

DROP INDEX IF EXISTS idx_status_engagement_counts_status_id;

DROP MATERIALIZED VIEW IF EXISTS status_engagement_counts CASCADE;
