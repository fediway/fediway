-- :up

CREATE TABLE IF NOT EXISTS enriched_statuses (
  status_id BIGINT PRIMARY KEY,
  author_id BIGINT,
  created_at TIMESTAMP,

  -- type
  is_reblog BOOLEAN,
  is_reply BOOLEAN,
  sensitive BOOLEAN,
  trendable BOOLEAN,
  visibility INT,
  num_chars INT,

  -- author
  author_domain VARCHAR,
  author_locked BOOLEAN,
  author_discoverable BOOLEAN,
  author_trendable BOOLEAN,
  author_indexable BOOLEAN,
  author_silenced_at TIMESTAMP,
  author_suspended_at TIMESTAMP,

  -- preview card
  has_link BOOLEAN,
  has_photo_link BOOLEAN,
  has_video_link BOOLEAN,
  has_rich_link BOOLEAN,
  preview_card_id BIGINT,
  preview_card_domain VARCHAR,

  -- poll
  has_poll BOOLEAN,
  num_poll_options INT,
  allows_multiple_poll_options BOOLEAN,
  hides_total_poll_options BOOLEAN,
  poll_id BIGINT,

  -- quote
  has_quote BOOLEAN,
  quoted_status_id BIGINT,
  quoted_account_id BIGINT,
  quote_state INT,

  -- media
  has_image BOOLEAN,
  has_gifv BOOLEAN,
  has_video BOOLEAN,
  has_audio BOOLEAN,
  num_media_attachments INT,
  ordered_media_attachment_ids BIGINT[],

  -- mentions
  num_mentions INT,
  mentions BIGINT[],

  -- tags
  num_tags INT,
  tags BIGINT[]
) ON CONFLICT DO UPDATE IF NOT NULL;

CREATE SINK IF NOT EXISTS enriched_statuses_statuses_sink
INTO enriched_statuses (
  status_id, 
  author_id,
  created_at,
  is_reblog,
  is_reply,
  sensitive,
  trendable,
  visibility,
  num_media_attachments,
  ordered_media_attachment_ids
) AS
SELECT 
  id, 
  account_id,
  created_at,
  (reblog_of_id IS NOT NULL) AS is_reblog,
  (in_reply_to_id IS NOT NULL) AS is_reply,
  sensitive,
  trendable,
  visibility,
  ARRAY_LENGTH(ordered_media_attachment_ids) AS num_media_attachments,
  ordered_media_attachment_ids
FROM statuses
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS enriched_statuses_author_sink
INTO enriched_statuses (
  status_id,
  author_domain,
  author_locked,
  author_discoverable,
  author_trendable,
  author_indexable,
  author_silenced_at,
  author_suspended_at
) AS
SELECT 
  s.id as status_id,
  a.domain AS author_domain,
  a.locked AS author_locked,
  a.discoverable AS author_discoverable,
  a.trendable AS author_trendable,
  a.indexable AS author_indexable,
  a.silenced_at AS author_silenced_at,
  a.suspended_at AS author_suspended_at
FROM statuses s
JOIN accounts a ON a.id = s.account_id
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS enriched_statuses_preview_cards_sink
INTO enriched_statuses (
  status_id,
  has_link,
  has_photo_link,
  has_video_link,
  has_rich_link,
  preview_card_id,
  preview_card_domain
) AS
SELECT 
  pcs.status_id,
  COALESCE(pc.type = 0, FALSE) AS has_link,
  COALESCE(pc.type = 1, FALSE) AS has_photo_link,
  COALESCE(pc.type = 2, FALSE) AS has_video_link,
  COALESCE(pc.type = 3, FALSE) AS has_rich_link,
  pc.id AS preview_card_id,
  pcd.domain AS preview_card_domain
FROM preview_cards_statuses pcs
JOIN preview_cards pc ON pc.id = pcs.preview_card_id
JOIN preview_card_domains pcd ON pcd.preview_card_id = pcs.preview_card_id
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS enriched_statuses_polls_sink
INTO enriched_statuses (
  status_id,
  has_poll,
  num_poll_options,
  allows_multiple_poll_options,
  hides_total_poll_options,
  poll_id
) AS
SELECT 
  status_id,
  true AS has_poll,
  ARRAY_LENGTH(options, 1) AS num_poll_options,
  multiple AS allows_multiple_poll_options,
  hide_totals AS hides_total_poll_options,
  id as poll_id
FROM polls
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS enriched_statuses_quotes_sink
INTO enriched_statuses (
  status_id,
  has_quote,
  quoted_account_id,
  quoted_status_id,
  quote_state
) AS
SELECT 
  status_id,
  true AS has_quote,
  quoted_account_id,
  quoted_status_id,
  state
FROM quotes
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS enriched_statuses_media_attachments_sink
INTO enriched_statuses (
  status_id,
  has_image,
  has_gifv,
  has_video,
  has_audio
) AS
SELECT
  status_id,
  BOOL_OR(type = 0) AS has_image,
  BOOL_OR(type = 1) AS has_gifv,
  BOOL_OR(type = 2) AS has_video,
  BOOL_OR(type = 4) AS has_audio
FROM media_attachments
GROUP BY status_id
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS enriched_statuses_mentions_sink
INTO enriched_statuses (
  status_id,
  num_mentions,
  mentions
) AS
SELECT 
  status_id,
  COUNT(account_id)::INT AS num_mentions,
  ARRAY_REMOVE(ARRAY_AGG(account_id), NULL) as mentions
FROM mentions
GROUP BY status_id
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS enriched_statuses_tags_sink
INTO enriched_statuses (
  status_id,
  num_tags,
  tags
) AS
SELECT 
  status_id,
  COUNT(tag_id)::INT AS num_tags,
  ARRAY_REMOVE(ARRAY_AGG(tag_id), NULL) as tags
FROM statuses_tags
GROUP BY status_id
WITH (
  type = 'append-only',
  force_append_only = 'true',
);

CREATE SINK IF NOT EXISTS enriched_statuses_sink AS
SELECT 
  *,
  created_at as event_time
FROM enriched_statuses
WHERE created_at > NOW() - INTERVAL '30 DAYS'
WITH (
  connector='kafka',
  properties.bootstrap.server='{{ bootstrap_server }}',
  topic='statuses',
  primary_key='status_id',
  properties.linger.ms='1000',
) FORMAT DEBEZIUM ENCODE JSON;

-- :down

DROP SINK IF EXISTS enriched_statuses_sink;
DROP SINK IF EXISTS enriched_statuses_tags_sink;
DROP SINK IF EXISTS enriched_statuses_mentions_sink;
DROP SINK IF EXISTS enriched_statuses_media_attachments_sink;
DROP SINK IF EXISTS enriched_statuses_preview_card_sink;
DROP SINK IF EXISTS enriched_statuses_polls_sink;
DROP SINK IF EXISTS enriched_statuses_quotes_sink;
DROP SINK IF EXISTS enriched_statuses_author_sink;
DROP SINK IF EXISTS enriched_statuses_statuses_sink;

DROP INDEX IF EXISTS idx_enriched_statuses_status_id;

DROP TABLE IF EXISTS enriched_statuses CASCADE;