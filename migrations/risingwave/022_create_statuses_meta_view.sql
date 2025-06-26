-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS statuses_meta AS
SELECT
  s.id as status_id,
  stats.favourites_count AS fav_count,
  stats.reblogs_count,
  stats.replies_count,
  COALESCE(media.has_image, FALSE) AS has_image,
  COALESCE(media.has_gifv, FALSE) AS has_gifv,
  COALESCE(media.has_video, FALSE) AS has_video,
  COALESCE(media.has_audio, FALSE) AS has_audio,
  COALESCE(mentions.num_mentions, 0) AS num_mentions,
  COALESCE(tags.num_tags, 0) AS num_tags,
  (s.reblog_of_id IS NOT NULL) AS is_reblog,
  (s.in_reply_to_id IS NOT NULL) AS is_reply
FROM statuses s
LEFT JOIN status_stats stats ON s.id = stats.status_id
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
LEFT JOIN (
  SELECT
    status_id,
    COUNT(account_id) AS num_mentions
  FROM mentions
  GROUP BY status_id
) mentions ON s.id = mentions.status_id
LEFT JOIN (
  SELECT
    status_id,
    COUNT(tag_id) AS num_tags
  FROM statuses_tags
  GROUP BY status_id
) tags ON s.id = tags.status_id;

-- :down

DROP VIEW IF EXISTS statuses_meta CASCADE;