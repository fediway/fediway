
-- :up
CREATE TABLE IF NOT EXISTS enriched_status_engagement_events (
  account_id BIGINT,
  status_id BIGINT,
  author_id BIGINT,
  domain VARCHAR,
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
  WATERMARK FOR event_time AS event_time - INTERVAL '1 DAY'
) APPEND ONLY ON CONFLICT IGNORE;

CREATE SINK IF NOT EXISTS enriched_status_engagement_events_sink
INTO enriched_status_engagement_events AS
SELECT
  e.account_id,
  e.status_id,
  s.account_id as author_id,
  a.domain,
  e.type,
  e.event_time,
  EXTRACT(EPOCH FROM (e.event_time - s.created_at))::BIGINT AS status_age_in_seconds,
  e.favourite_id,
  e.reblog_id,
  e.reply_id,
  m.fav_count,
  m.reblogs_count,
  m.replies_count,
  m.has_image,
  m.has_gifv,
  m.has_video,
  m.has_audio,
  m.num_mentions
FROM status_engagements e
JOIN accounts a ON e.account_id = a.id
JOIN statuses s ON s.id = e.status_id
JOIN statuses_meta m ON m.status_id = e.status_id
WITH (type = 'append-only', force_append_only='true');

-- :down
DROP SINK IF EXISTS enriched_status_engagement_events_sink;
DROP TABLE IF EXISTS enriched_status_engagement_events CASCADE;