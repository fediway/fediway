
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS follows_recent_engagements AS
SELECT
    f.account_id AS user_id,
    e.status_id,
    e.author_id,
    COUNT(DISTINCT f.target_account_id) AS engaged_follows_count,
    ARRAY_AGG(DISTINCT f.target_account_id) AS engaged_follows,
    MAX(e.event_time) AS latest_engagement_time,
    SUM(CASE e.type
        WHEN 0 THEN 1.0   -- fav
        WHEN 1 THEN 2.0   -- reblog
        WHEN 2 THEN 3.0   -- reply
        WHEN 5 THEN 2.0   -- quote
        ELSE 0
    END) AS total_engagement_weight
FROM follows f
JOIN local_accounts la ON la.account_id = f.account_id
JOIN enriched_status_engagement_events e
    ON e.account_id = f.target_account_id
WHERE e.event_time > NOW() - INTERVAL '6 HOURS'
GROUP BY f.account_id, e.status_id, e.author_id
HAVING COUNT(DISTINCT f.target_account_id) >= 1;

CREATE INDEX IF NOT EXISTS idx_follows_recent_engagements_user_id
    ON follows_recent_engagements(user_id);

CREATE INDEX IF NOT EXISTS idx_follows_recent_engagements_engaged_count
    ON follows_recent_engagements(user_id, engaged_follows_count DESC);

-- :down

DROP INDEX IF EXISTS idx_follows_recent_engagements_user_id;
DROP INDEX IF EXISTS idx_follows_recent_engagements_engaged_count;

DROP MATERIALIZED VIEW IF EXISTS follows_recent_engagements CASCADE;
