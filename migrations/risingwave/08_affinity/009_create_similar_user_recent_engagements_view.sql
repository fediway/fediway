
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS similar_user_recent_engagements AS
SELECT
    sim.user_id,
    e.status_id,
    e.author_id,
    e.type,
    e.event_time,
    sim.similarity,
    CASE e.type
        WHEN 0 THEN 1.0
        WHEN 1 THEN 2.0
        WHEN 2 THEN 3.0
        WHEN 5 THEN 2.0
        ELSE 0
    END AS engagement_weight
FROM user_top_similar sim
JOIN enriched_status_engagement_events e ON e.account_id = sim.similar_user_id
JOIN statuses s ON s.id = e.status_id
WHERE e.event_time > NOW() - INTERVAL '48 HOURS'
  AND e.type IN (0, 1, 2, 5)
  AND s.visibility = 0
  AND s.deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_similar_user_recent_engagements_user_id
    ON similar_user_recent_engagements(user_id);

CREATE INDEX IF NOT EXISTS idx_similar_user_recent_engagements_status
    ON similar_user_recent_engagements(user_id, status_id);

-- :down

DROP INDEX IF EXISTS idx_similar_user_recent_engagements_status;
DROP INDEX IF EXISTS idx_similar_user_recent_engagements_user_id;

DROP MATERIALIZED VIEW IF EXISTS similar_user_recent_engagements CASCADE;
