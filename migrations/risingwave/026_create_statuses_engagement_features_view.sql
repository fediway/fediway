-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS status_engagement_features AS
SELECT 
    e.status_id, 
    e.window_start, 
    e.window_end,
    COUNT(*) AS engagement_speed,
    COALESCE((
    	COUNT(*) - 
    	(LAG(COUNT(*)) OVER (PARTITION BY e.status_id ORDER BY e.window_start))
    ), 0) as engagement_velocity
FROM TUMBLE(enriched_status_engagement_events, event_time, INTERVAL '60 MINUTES') e
WHERE e.account_id != e.author_id -- ignore engagements by author on their own status
GROUP BY e.status_id, e.window_start, e.window_end;

CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality AS
SELECT 
    s.id as status_id,
    (
    	MAX(e_curr.engagement_velocity) * 0.4 +
    	MAX(e_curr.engagement_speed) * 0.3 +
    	AVG(e_all.engagement_speed) * 0.2 +
    	MAX(e_all.engagement_speed) * 0.1 +
    	SUM(e_all.engagement_speed) * 0.05
    ) as virality_score
FROM statuses s
JOIN status_engagement_features e_curr
ON e_curr.status_id = s.id 
AND e_curr.window_start < NOW() - INTERVAL '60 MINUTES'
AND e_curr.window_start > NOW() - INTERVAL '120 MINUTES'
JOIN status_engagement_features e_all
ON e_all.status_id = s.id
GROUP BY s.id;

-- :down

DROP VIEW IF EXISTS status_engagement_features CASCADE;
DROP VIEW IF EXISTS status_virality CASCADE;