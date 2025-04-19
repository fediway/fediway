-- :up
CREATE MATERIALIZED VIEW enriched_status_engagements AS
SELECT
  e.account_id,
  e.status_id,
  MAX(s.account_id) as author_id,
  e.type,
  e.event_time,
  MAX(s.created_at) AS status_event_time,
  MAX(f.fav_count) as fav_count,
  MAX(f.reblogs_count) as reblogs_count,
  MAX(f.replies_count) as replies_count,
  bool_or(f.has_image) AS has_image,
  bool_or(f.has_gifv) AS has_gifv,
  bool_or(f.has_video) AS has_video,
  bool_or(f.has_audio) AS has_audio,
  MAX(f.num_mentions) AS num_mentions
FROM status_engagements e
JOIN statuses s ON s.id = e.status_id
JOIN status_features f ON f.status_id = e.status_id
GROUP BY e.account_id, e.status_id, e.event_time, e.type;

-- :down
DROP VIEW IF EXISTS enriched_status_engagements;