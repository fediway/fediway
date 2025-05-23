-
-- :up
CREATE TABLE IF NOT EXISTS enriched_status_engagement_events (
  account_id BIGINT,
  status_id BIGINT,
  author_id BIGINT,
  type VARCHAR,
  event_time TIMESTAMP,
  status_age_in_seconds BIGINT,
  favourite_id BIGINT,
  reblog_id BIGINT,
  reply_id BIGINT,
  fav_count BIGINT,
  reblogs_count BIGINT,
  replies_count BIGINT,
  has_image BOOLEAN DEFAULT false,
  has_gifv BOOLEAN DEFAULT false,
  has_video BOOLEAN DEFAULT false,
  has_audio BOOLEAN DEFAULT false,
  num_mentions BIGINT,
  PRIMARY KEY (account_id, status_id, type),
  WATERMARK FOR event_time AS event_time - INTERVAL '1 minute'
) APPEND ONLY ON CONFLICT IGNORE;

CREATE SINK IF NOT EXISTS enriched_status_engagement_events_sink
INTO enriched_status_engagement_events AS
SELECT
  e.account_id,
  e.status_id,
  s.account_id as author_id,
  e.type,
  e.event_time,
  EXTRACT(EPOCH FROM (e.event_time - MAX(s.created_at)))::BIGINT AS status_age_in_seconds,
  MAX(e.favourite_id) as favourite_id,
  MAX(e.reblog_id) as reblog_id,
  MAX(e.reply_id) as reply_id,
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
GROUP BY 
  e.account_id, 
  e.status_id, 
  s.account_id,
  e.event_time, 
  e.type
WITH (type = 'append-only', force_append_only='true');

-- :down
DROP SINK IF EXISTS enriched_status_engagement_events_sink;
DROP TABLE IF EXISTS enriched_status_engagement_events CASCADE;