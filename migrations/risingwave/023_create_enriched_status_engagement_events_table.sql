
-- :up

CREATE TABLE IF NOT EXISTS enriched_status_engagement_events (
  account_id BIGINT,
  status_id BIGINT,
  author_id BIGINT,
  source_domain VARCHAR,
  target_domain VARCHAR,
  type INT,
  event_time TIMESTAMP,
  status_age_in_seconds BIGINT,
  favourite_id BIGINT,
  reblog_id BIGINT,
  reply_id BIGINT,
  poll_vote_id BIGINT,
  bookmark_id BIGINT,
  fav_count BIGINT DEFAULT 0,
  reblogs_count BIGINT DEFAULT 0,
  replies_count BIGINT DEFAULT 0,
  has_link BOOLEAN DEFAULT false,
  has_photo_link BOOLEAN DEFAULT false,
  has_video_link BOOLEAN DEFAULT false,
  has_rich_link BOOLEAN DEFAULT false,
  has_poll BOOLEAN DEFAULT false,
  num_poll_options INT DEFAULT 0,
  allows_multiple_poll_options BOOLEAN DEFAULT false,
  hides_total_poll_options BOOLEAN DEFAULT false,
  has_image BOOLEAN DEFAULT false,
  has_gifv BOOLEAN DEFAULT false,
  has_video BOOLEAN DEFAULT false,
  has_audio BOOLEAN DEFAULT false,
  num_media_attachments INT DEFAULT 0,
  num_mentions INT DEFAULT 0,
  num_tags INT DEFAULT 0,
  PRIMARY KEY (account_id, status_id, type),

  -- wait at most 1 day for late arriving engagements
  WATERMARK FOR event_time AS event_time - INTERVAL '1 DAY' 
) APPEND ONLY ON CONFLICT IGNORE;

CREATE SINK IF NOT EXISTS enriched_status_engagement_events_sink
INTO enriched_status_engagement_events AS
SELECT
  e.account_id,
  e.status_id,
  s.account_id as author_id,
  account.domain as source_domain,
  author.domain as target_domain,
  e.type,
  e.event_time,
  EXTRACT(EPOCH FROM (e.event_time - s.created_at))::BIGINT AS status_age_in_seconds,
  e.favourite_id,
  e.reblog_id,
  e.reply_id,
  e.poll_vote_id,
  e.bookmark_id,
  st.favourites_count,
  st.reblogs_count,
  st.replies_count,
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
  m.num_media_attachments::INT,
  m.num_mentions::INT,
  m.num_tags::INT
FROM status_engagements e
JOIN statuses s ON s.id = e.status_id
JOIN accounts account ON e.account_id = account.id
JOIN accounts author ON s.account_id = author.id
JOIN status_stats st ON st.status_id = e.status_id
JOIN status_meta m ON m.status_id = e.status_id
WITH (type = 'append-only', force_append_only='true');

CREATE INDEX IF NOT EXISTS idx_enriched_status_engagement_events_event_time ON enriched_status_engagement_events(event_time); 


-- :down

DROP SINK IF EXISTS enriched_status_engagement_events_sink;

DROP INDEX IF EXISTS idx_enriched_status_engagement_events_event_time;

DROP TABLE IF EXISTS enriched_status_engagement_events CASCADE;