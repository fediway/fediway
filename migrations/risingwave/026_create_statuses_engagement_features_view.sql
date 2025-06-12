-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS status_engagement_features AS
SELECT 
    e.status_id, 
    e.window_start, 
    e.window_end,
    COUNT(distinct e.domain) AS engaged_domains,
    COUNT(*) AS engagement_speed,
    COALESCE((
    	COUNT(*) - 
    	(LAG(COUNT(*)) OVER (PARTITION BY e.status_id ORDER BY e.window_start))
    ), 0) as engagement_velocity
FROM TUMBLE(enriched_status_engagement_events, event_time, INTERVAL '60 MINUTES') e
WHERE e.account_id != e.author_id -- ignore engagements by author on their own status
GROUP BY e.status_id, e.window_start, e.window_end;

-- :down

DROP VIEW IF EXISTS status_engagement_features CASCADE;