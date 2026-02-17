
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_active AS
SELECT account_id AS user_id
FROM enriched_status_engagement_events
WHERE event_time > NOW() - INTERVAL '60 DAYS'
GROUP BY account_id
HAVING COUNT(*) >= 10;

CREATE INDEX IF NOT EXISTS idx_user_active_user_id
    ON user_active(user_id);

-- :down

DROP INDEX IF EXISTS idx_user_active_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_active CASCADE;
