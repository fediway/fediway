-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality_stats AS
SELECT 
  e.status_id, 
  e.window_start, 
  e.window_end,
  COUNT(DISTINCT e.target_domain) AS engaged_domains,
  COUNT(*) AS engagement_speed,
  COALESCE((
    COUNT(*) - 
    (LAG(COUNT(*)) OVER (PARTITION BY e.status_id ORDER BY e.window_start))
  ), 0) as engagement_velocity
FROM HOP(enriched_status_engagement_events, event_time, INTERVAL '1 HOUR', INTERVAL '2 HOURS') e
WHERE e.account_id != e.author_id -- ignore engagements by author on their own status
GROUP BY e.status_id, e.window_start, e.window_end;

CREATE INDEX IF NOT EXISTS status_virality_stats_window_start_status_id ON status_virality_stats(window_start DESC, status_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality_aggregates AS
SELECT 
  status_id,
  MAX(engagement_velocity) as max_engagement_velocity,
  MAX(engaged_domains) as max_engaged_domains,
  MAX(engagement_speed) as max_engagement_speed,
  AVG(engagement_speed) as avg_engagement_speed
FROM status_virality_stats
GROUP BY status_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality_scores AS
SELECT 
  current_stats.status_id,
  (
    current_stats.engagement_velocity * 0.5 +
    current_stats.engaged_domains * 0.4 +
    current_stats.engagement_speed * 0.3 +
    agg.avg_engagement_speed * 0.2 +
    agg.max_engagement_velocity * 0.1
  ) as score
FROM status_virality_aggregates agg
JOIN status_virality_stats current_stats ON agg.status_id = current_stats.status_id
WHERE current_stats.window_start > NOW() - INTERVAL '2 HOURS'
  AND current_stats.window_start < NOW() - INTERVAL '1 HOUR';

CREATE INDEX IF NOT EXISTS status_virality_scores_status_id ON status_virality_scores(status_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality_score_languages AS
SELECT
  scores.*,
  s.language
FROM status_virality_scores scores
JOIN statuses s ON s.id = scores.status_id;

-- CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality_score_languages AS
-- SELECT language
-- FROM status_virality_scores
-- GROUP BY language;

-- :down

DROP VIEW IF EXISTS status_virality_score_languages CASCADE;
DROP VIEW IF EXISTS status_virality_scores CASCADE;
DROP VIEW IF EXISTS status_virality_aggregates CASCADE;
DROP VIEW IF EXISTS status_virality_stats CASCADE;