-- :up
CREATE MATERIALIZED VIEW IF NOT EXISTS status_features AS
SELECT
  s.id as status_id,
  MAX(st.favourites_count) AS fav_count,
  MAX(st.reblogs_count) AS reblogs_count,
  MAX(st.replies_count) AS replies_count,
  bool_or(m.type = 0) AS has_image,
  bool_or(m.type = 1) AS has_gifv,
  bool_or(m.type = 2) AS has_video,
  bool_or(m.type = 4) AS has_audio,
  COUNT(DISTINCT me.account_id) AS num_mentions,
  s.reblog_of_id IS NOT NULL AS is_reblog,
  s.in_reply_to_id IS NOT NULL AS is_reply
FROM statuses s
LEFT JOIN media_attachments m ON s.id = m.status_id
LEFT JOIN mentions me ON s.id = me.status_id
LEFT JOIN status_stats st ON s.id = st.status_id
GROUP BY s.id, s.reblog_of_id, s.in_reply_to_id;

-- :down
DROP VIEW IF EXISTS status_features;