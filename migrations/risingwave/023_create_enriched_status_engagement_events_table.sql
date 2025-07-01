
-- :up

CREATE TABLE IF NOT EXISTS enriched_status_engagement_events (
  account_id BIGINT,
  status_id BIGINT,
  author_id BIGINT,
  domain VARCHAR,
  type INT,
  event_time TIMESTAMP,
  status_age_in_seconds BIGINT,
  favourite_id BIGINT,
  reblog_id BIGINT,
  reply_id BIGINT,
  poll_vote_id BIGINT,
  bookmark_id BIGINT,
  fav_count BIGINT,
  reblogs_count BIGINT,
  replies_count BIGINT,
  has_link BOOLEAN,
  has_photo_link BOOLEAN,
  has_video_link BOOLEAN,
  has_rich_link BOOLEAN,
  has_poll BOOLEAN,
  num_poll_options INT,
  allows_multiple_poll_options BOOLEAN,
  hides_total_poll_options BOOLEAN,
  has_image BOOLEAN DEFAULT false,
  has_gifv BOOLEAN DEFAULT false,
  has_video BOOLEAN DEFAULT false,
  has_audio BOOLEAN DEFAULT false,
  num_mentions BIGINT,
  num_tags BIGINT,
  PRIMARY KEY (account_id, status_id, type),

  -- wait at most 1 day for late arriving engagements
  WATERMARK FOR event_time AS event_time - INTERVAL '1 DAY' 
) APPEND ONLY ON CONFLICT IGNORE;

CREATE INDEX IF NOT EXISTS idx_enriched_status_engagement_events_event_time ON enriched_status_engagement_events(event_time); 

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
  e.poll_vote_id,
  e.bookmark_id,
  m.fav_count,
  m.reblogs_count,
  m.replies_count,
  m.has_link,
  m.has_photo_link,
  m.has_video_link,
  m.has_rich_link,
  m.has_poll,
  m.num_poll_options,
  m.allows_multiple_poll_options,
  m.hides_total_poll_options,
  m.has_image,
  m.has_gifv,
  m.has_video,
  m.has_audio,
  m.num_mentions,
  m.num_tags
FROM status_engagements e
JOIN accounts a ON e.account_id = a.id
JOIN statuses s ON s.id = e.status_id
JOIN statuses_meta m ON m.status_id = e.status_id
WITH (type = 'append-only', force_append_only='true');

-- :down

DROP SINK IF EXISTS enriched_status_engagement_events_sink;

DROP INDEX IF EXISTS idx_enriched_status_engagement_events_event_time;

DROP TABLE IF EXISTS enriched_status_engagement_events CASCADE;