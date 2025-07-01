-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS statuses_meta AS
SELECT
  s.id as status_id,

  -- type
  (s.reblog_of_id IS NOT NULL) AS is_reblog,
  (s.in_reply_to_id IS NOT NULL) AS is_reply,

  -- stats
  stats.favourites_count AS fav_count,
  stats.reblogs_count,
  stats.replies_count,

  -- preview card
  COALESCE(links.has_link, FALSE) AS has_link,
  COALESCE(links.has_photo_link, FALSE) AS has_photo_link,
  COALESCE(links.has_video_link, FALSE) AS has_video_link,
  COALESCE(links.has_rich_link, FALSE) AS has_rich_link,

  -- preview card
  p.status_id IS NOT NULL AS has_poll,
  ARRAY_LENGTH(p.options, 1) AS num_poll_options,
  p.multiple AS allows_multiple_poll_options,
  p.hide_totals AS hides_total_poll_options,

  -- media
  COALESCE(media.has_image, FALSE) AS has_image,
  COALESCE(media.has_gifv, FALSE) AS has_gifv,
  COALESCE(media.has_video, FALSE) AS has_video,
  COALESCE(media.has_audio, FALSE) AS has_audio,

  -- mentions
  COALESCE(mentions.num_mentions, 0) AS num_mentions,

  -- tags
  COALESCE(tags.num_tags, 0) AS num_tags

FROM statuses s

-- stats
LEFT JOIN status_stats stats ON s.id = stats.status_id

-- preview cards
LEFT JOIN (
  SELECT 
    status_id,
    BOOL_OR(type = 0) AS has_link,
    BOOL_OR(type = 1) AS has_photo_link,
    BOOL_OR(type = 2) AS has_video_link,
    BOOL_OR(type = 3) AS has_rich_link
  FROM preview_cards_statuses pcs
  JOIN preview_cards pc ON pc.id = pcs.preview_card_id
  GROUP BY status_id
) links ON s.id = links.status_id

-- poll
LEFT JOIN polls p ON s.id = p.status_id

-- media
LEFT JOIN (
  SELECT
    status_id,
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
    COUNT(account_id) AS num_mentions
  FROM mentions
  GROUP BY status_id
) mentions ON s.id = mentions.status_id

-- tags
LEFT JOIN (
  SELECT 
    status_id,
    COUNT(tag_id) AS num_tags
  FROM statuses_tags
  GROUP BY status_id
) tags ON s.id = tags.status_id;

-- :down

DROP VIEW IF EXISTS statuses_meta CASCADE;