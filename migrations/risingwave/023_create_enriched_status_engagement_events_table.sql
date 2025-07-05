
-- :up

CREATE TABLE IF NOT EXISTS enriched_status_engagement_events (
  account_id BIGINT,
  status_id BIGINT,
  author_id BIGINT,
  type INT,
  event_time TIMESTAMP,
  status_age_in_seconds BIGINT,
  favourite_id BIGINT,
  reblog_id BIGINT,
  reply_id BIGINT,
  poll_vote_id BIGINT,
  bookmark_id BIGINT,

  -- account
  source_domain VARCHAR,
  account_locked BOOLEAN DEFAULT false,
  account_discoverable BOOLEAN DEFAULT true,
  account_trendable BOOLEAN DEFAULT true,
  account_indexable BOOLEAN DEFAULT true,
  account_silenced_at TIMESTAMP,
  account_suspended_at TIMESTAMP,

  -- author
  target_domain VARCHAR,
  author_locked BOOLEAN DEFAULT false,
  author_discoverable BOOLEAN DEFAULT true,
  author_trendable BOOLEAN DEFAULT true,
  author_indexable BOOLEAN DEFAULT true,
  author_silenced_at TIMESTAMP,
  author_suspended_at TIMESTAMP,

  -- status
  sensitive BOOLEAN DEFAULT false,
  visibility INT,
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

  -- stats
  fav_count BIGINT DEFAULT 0,
  reblogs_count BIGINT DEFAULT 0,
  replies_count BIGINT DEFAULT 0,

  PRIMARY KEY (account_id, status_id, type),

  -- due to federation events may arrive late
  -- we wait at most 1 day for late arriving engagements
  WATERMARK FOR event_time AS event_time - INTERVAL '1 DAY'
) APPEND ONLY ON CONFLICT IGNORE;

CREATE SINK IF NOT EXISTS enriched_status_engagement_events_sink
INTO enriched_status_engagement_events AS
SELECT
  e.account_id,
  e.status_id,
  s.author_id,
  e.type,
  e.event_time,
  EXTRACT(EPOCH FROM (e.event_time - s.created_at))::BIGINT AS status_age_in_seconds,
  e.favourite_id,
  e.reblog_id,
  e.reply_id,
  e.poll_vote_id,
  e.bookmark_id,
  
  -- account
  a.domain as source_domain,
  a.locked AS account_locked,
  a.discoverable AS account_discoverable,
  a.trendable AS account_trendable,
  a.indexable AS account_indexable,
  a.silenced_at AS account_silenced_at,
  a.suspended_at AS account_suspended_at,

  -- author
  s.author_domain as target_domain,
  s.author_locked,
  s.author_discoverable,
  s.author_trendable,
  s.author_indexable,
  s.author_silenced_at,
  s.author_suspended_at,

  -- status
  s.sensitive,
  s.visibility,
  s.has_link,
  s.has_photo_link,
  s.has_video_link,
  s.has_rich_link,
  s.has_poll,
  s.num_poll_options,
  s.allows_multiple_poll_options,
  s.hides_total_poll_options,
  s.has_image,
  s.has_gifv,
  s.has_video,
  s.has_audio,
  s.num_media_attachments::INT,
  s.num_mentions::INT,
  s.num_tags::INT,

  -- stats
  st.favourites_count,
  st.reblogs_count,
  st.replies_count
FROM status_engagements e
JOIN accounts a ON e.account_id = a.id
JOIN status_stats st ON st.status_id = e.status_id
JOIN enriched_statuses s ON s.status_id = e.status_id
WITH (type = 'append-only', force_append_only='true');

CREATE INDEX IF NOT EXISTS idx_enriched_status_engagement_events_event_time ON enriched_status_engagement_events(event_time); 

CREATE SINK IF NOT EXISTS enriched_status_engagement_events_sink AS
SELECT *
FROM enriched_status_engagement_events
WHERE event_time > NOW() - INTERVAL '3 DAYS'
WITH (
  connector='kafka',
  properties.bootstrap.server='{{ bootstrap_server }}',
  topic='status_engagements',
  primary_key='account_id,status_id',
) FORMAT PLAIN ENCODE JSON (
  force_append_only='true'
);

-- :down

DROP SINK IF EXISTS enriched_status_engagement_events_sink;

DROP INDEX IF EXISTS idx_enriched_status_engagement_events_event_time;

DROP TABLE IF EXISTS enriched_status_engagement_events CASCADE;