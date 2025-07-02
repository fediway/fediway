-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality_stats AS
SELECT 
    e.status_id, 
    e.window_start, 
    e.window_end,
    APPROX_COUNT_DISTINCT(e.target_domain) AS engaged_domains,
    COUNT(*) AS engagement_speed,
    COALESCE((
    	COUNT(*) - 
    	(LAG(COUNT(*)) OVER (PARTITION BY e.status_id ORDER BY e.window_start))
    ), 0) as engagement_velocity
FROM TUMBLE(enriched_status_engagement_events, event_time, INTERVAL '60 MINUTES') e
WHERE e.account_id != e.author_id -- ignore engagements by author on their own status
GROUP BY e.status_id, e.window_start, e.window_end;

CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality_scores AS
SELECT 
    stats_current.status_id,
    (
    	MAX(stats_current.engagement_velocity) * 0.5 +
    	MAX(stats_current.engaged_domains) * 0.4 +
    	MAX(stats_current.engagement_speed) * 0.3 +
    	AVG(stats_all.engagement_speed) * 0.2 +
    	MAX(stats_all.engagement_speed) * 0.1
    ) as score
FROM status_virality_stats stats_current
JOIN status_virality_stats stats_all ON stats_all.status_id = stats_current.status_id
WHERE stats_current.window_start < NOW()
  AND stats_current.window_start > NOW() - INTERVAL '120 MINUTES'
GROUP BY stats_current.status_id;

-- :down

DROP VIEW IF EXISTS status_virality_stats CASCADE;
DROP VIEW IF EXISTS status_virality_scores CASCADE;