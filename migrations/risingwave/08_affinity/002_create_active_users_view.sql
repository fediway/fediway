
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS active_users AS
SELECT account_id
FROM enriched_status_engagement_events
WHERE event_time > NOW() - INTERVAL '60 DAYS'
GROUP BY account_id
HAVING COUNT(*) >= 10;

CREATE INDEX IF NOT EXISTS idx_active_users_account_id
    ON active_users(account_id);

-- :down

DROP INDEX IF EXISTS idx_active_users_account_id;

DROP MATERIALIZED VIEW IF EXISTS active_users CASCADE;
