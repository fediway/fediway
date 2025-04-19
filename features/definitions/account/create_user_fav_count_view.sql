-- :up
CREATE MATERIALIZED VIEW user_like_count_30m AS
SELECT
  user_id,
  window_start,
  COUNT(*) AS cnt
FROM HOP(
  (SELECT user_id, created_at
   FROM status_engagements
   WHERE engagement_type = 'favourite'),
  created_at,
  INTERVAL '5 MINUTES',
  INTERVAL '30 MINUTES'
)
GROUP BY user_id, window_start;

-- :down
