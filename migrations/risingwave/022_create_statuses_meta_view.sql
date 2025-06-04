-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS statuses_meta AS
SELECT
  s.id as status_id,
  MAX(stats.favourites_count) AS fav_count,
  MAX(stats.reblogs_count) AS reblogs_count,
  MAX(stats.replies_count) AS replies_count,
  bool_or(m.type = 0) AS has_image,
  bool_or(m.type = 1) AS has_gifv,
  bool_or(m.type = 2) AS has_video,
  bool_or(m.type = 4) AS has_audio,
  COUNT(DISTINCT me.account_id) AS num_mentions,
  COUNT(DISTINCT st.tag_id) AS num_tags,
  MAX(s.reblog_of_id) IS NOT NULL AS is_reblog,
  MAX(s.in_reply_to_id) IS NOT NULL AS is_reply
FROM statuses s
LEFT JOIN media_attachments m ON s.id = m.status_id
LEFT JOIN mentions me ON s.id = me.status_id
LEFT JOIN status_stats stats ON s.id = stats.status_id
LEFT JOIN statuses_tags st ON s.id = st.status_id
GROUP BY s.id;

-- :down

DROP VIEW IF EXISTS statuses_meta CASCADE;