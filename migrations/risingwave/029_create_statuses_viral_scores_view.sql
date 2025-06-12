-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS status_viral_scores AS
SELECT 
    s.id as status_id,
    (
    	MAX(e_curr.engagement_velocity) * 0.5 +
    	MAX(e_curr.engaged_domains) * 0.4 +
    	MAX(e_curr.engagement_speed) * 0.3 +
    	AVG(e_all.engagement_speed) * 0.2 +
    	MAX(e_all.engagement_speed) * 0.1
    ) as score
FROM statuses s
JOIN status_engagement_features e_curr
ON e_curr.status_id = s.id 
AND e_curr.window_start < NOW() - INTERVAL '60 MINUTES'
AND e_curr.window_start > NOW() - INTERVAL '120 MINUTES'
JOIN status_engagement_features e_all ON e_all.status_id = s.id
GROUP BY s.id;

CREATE SINK IF NOT EXISTS status_viral_scores_sink 
FROM status_viral_scores
WITH (
    primary_key = 'status_id',
    connector = 'redis',
    redis.url= '{{ redis_url }}',
) FORMAT PLAIN ENCODE TEMPLATE (
    force_append_only='true',
    key_format = 'score:viral:{status_id}',
    value_format = '{score}'
);

-- :down

DROP VIEW IF EXISTS status_viral_scores CASCADE;