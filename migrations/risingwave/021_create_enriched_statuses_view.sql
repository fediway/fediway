-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS enriched_statuses AS
SELECT
  s.id AS status_id,
  s.account_id AS author_id,
  s.created_at,

  -- type
  (s.reblog_of_id IS NOT NULL) AS is_reblog,
  (s.in_reply_to_id IS NOT NULL) AS is_reply,
  s.sensitive,
  s.visibility,

  -- author
  a.domain AS author_domain,
  a.locked AS author_locked,
  a.discoverable AS author_discoverable,
  a.trendable AS author_trendable,
  a.indexable AS author_indexable,
  a.silenced_at AS author_silenced_at,
  a.suspended_at AS author_suspended_at,

  -- preview card
  COALESCE(pc.type = 0, FALSE) AS has_link,
  COALESCE(pc.type = 1, FALSE) AS has_photo_link,
  COALESCE(pc.type = 2, FALSE) AS has_video_link,
  COALESCE(pc.type = 3, FALSE) AS has_rich_link,
  pc.id AS preview_card_id,
  pcd.domain AS preview_card_domain,

  -- preview card
  p.status_id IS NOT NULL AS has_poll,
  ARRAY_LENGTH(p.options, 1) AS num_poll_options,
  p.multiple AS allows_multiple_poll_options,
  p.hide_totals AS hides_total_poll_options,
  p.id as poll_id,

  -- media
  COALESCE(media.has_image, FALSE) AS has_image,
  COALESCE(media.has_gifv, FALSE) AS has_gifv,
  COALESCE(media.has_video, FALSE) AS has_video,
  COALESCE(media.has_audio, FALSE) AS has_audio,
  COALESCE(media.num_media_attachments, 0)::INT AS num_media_attachments,
  media.media_attachments AS media_attachments,

  -- mentions
  COALESCE(mentions.num_mentions, 0)::INT AS num_mentions,
  mentions.mentions,

  -- tags
  COALESCE(tags.num_tags, 0)::INT AS num_tags,
  tags.tags

FROM statuses s

-- account
JOIN accounts a ON a.id = s.account_id

-- preview cards
LEFT JOIN (
  SELECT 
    status_id,
    MIN(pcs.preview_card_id) AS preview_card_id
  FROM preview_cards_statuses pcs
  GROUP BY status_id
) pcs ON s.id = pcs.status_id
LEFT JOIN preview_cards pc ON pc.id = pcs.preview_card_id
LEFT JOIN preview_card_domains pcd ON pcd.preview_card_id = pcs.preview_card_id

-- poll
LEFT JOIN polls p ON s.id = p.status_id

-- media
LEFT JOIN (
  SELECT
    status_id,
    COUNT(id) AS num_media_attachments,
    ARRAY_REMOVE(ARRAY_AGG(account_id), NULL) as media_attachments,
    BOOL_OR(type = 0) AS has_image,
    BOOL_OR(type = 1) AS has_gifv,
    BOOL_OR(type = 2) AS has_video,
    BOOL_OR(type = 4) AS has_audio
  FROM media_attachments
  GROUP BY status_id
) media ON s.id = media.status_id

-- mentions
LEFT JOIN (
  SELECT 
    status_id,
    COUNT(account_id) AS num_mentions,
    ARRAY_REMOVE(ARRAY_AGG(account_id), NULL) as mentions
  FROM mentions
  GROUP BY status_id
) mentions ON s.id = mentions.status_id

-- tags
LEFT JOIN (
  SELECT 
    status_id,
    COUNT(tag_id) AS num_tags,
    ARRAY_REMOVE(ARRAY_AGG(tag_id), NULL) as tags
  FROM statuses_tags
  GROUP BY status_id
) tags ON s.id = tags.status_id;

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

DROP VIEW IF EXISTS enriched_statuses CASCADE;