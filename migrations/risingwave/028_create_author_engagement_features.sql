
-- :up
{% for window_size, spec in [('24 HOURS', '1d'), ('7 DAYS', '7d'), ('60 DAYS', '60d')] %}
  CREATE MATERIALIZED VIEW IF NOT EXISTS online_features_author_engagement_{{ spec }} AS
  SELECT
    MAX(event_time)::TIMESTAMP as event_time,
    e.author_id,
    COUNT(*) AS num_all,
    COUNT(*) FILTER (WHERE type = 0) AS num_favs,
    COUNT(*) FILTER (WHERE type = 1) AS num_reblogs,
    COUNT(*) FILTER (WHERE type = 2) AS num_replies,
    COUNT(*) FILTER (WHERE type = 3) AS num_poll_votes,
    COUNT(*) FILTER (WHERE type = 4) AS num_bookmarks,
    COUNT(*) FILTER (WHERE type = 5) AS num_quotes,
    COUNT(*) FILTER (WHERE has_link) as num_has_link,
    COUNT(*) FILTER (WHERE has_photo_link) as num_has_photo_link,
    COUNT(*) FILTER (WHERE has_video_link) as num_has_video_link,
    COUNT(*) FILTER (WHERE has_rich_link) as num_has_rich_link,
    COUNT(*) FILTER (WHERE has_poll) as num_has_poll,
    COUNT(*) FILTER (WHERE has_image) as num_has_image,
    COUNT(*) FILTER (WHERE has_gifv) as num_has_gifv,
    COUNT(*) FILTER (WHERE has_video) as num_has_video,
    COUNT(*) FILTER (WHERE has_audio) as num_has_audio,
    COUNT(*) FILTER (WHERE has_quote) as num_has_quote,
    AVG(text_chars_count) AS avg_text_chars_count,
    MAX(text_chars_count) AS max_text_chars_count,
    MIN(text_chars_count) AS min_text_chars_count,
    AVG(text_uppercase_count) AS avg_text_uppercase_count,
    MAX(text_uppercase_count) AS max_text_uppercase_count,
    MIN(text_uppercase_count) AS min_text_uppercase_count,
    AVG(text_newlines_count) AS avg_text_newlines_count,
    MAX(text_newlines_count) AS max_text_newlines_count,
    MIN(text_newlines_count) AS min_text_newlines_count,
    AVG(text_custom_emojis_count) AS avg_text_custom_emojis_count,
    MAX(text_custom_emojis_count) AS max_text_custom_emojis_count,
    MIN(text_custom_emojis_count) AS min_text_custom_emojis_count,
    AVG(fav_count) AS avg_status_fav_count,
    MAX(fav_count) AS max_status_fav_count,
    MIN(fav_count) AS min_status_fav_count,
    AVG(reblogs_count) AS avg_status_reblogs_count,
    MAX(reblogs_count) AS max_status_reblogs_count,
    MIN(reblogs_count) AS min_status_reblogs_count,
    AVG(replies_count) AS avg_status_replies_count,
    MAX(replies_count) AS max_status_replies_count,
    MIN(replies_count) AS min_status_replies_count,
    AVG(num_mentions) AS avg_mentions,
    AVG(num_tags) AS avg_tags
  FROM enriched_status_engagement_events e
  WHERE event_time >= NOW() - INTERVAL '{{ window_size }}'
  GROUP BY e.author_id;
  
  CREATE SINK IF NOT EXISTS online_features_author_engagement_{{ spec }}_sink
  FROM online_features_author_engagement_{{ spec }}
  WITH (
    connector='kafka',
    properties.bootstrap.server='{{ bootstrap_server }}',
    topic='online_features_author_engagement_{{ spec }}',
    primary_key='author_id',
    properties.linger.ms='10000',
  ) FORMAT PLAIN ENCODE JSON (
    force_append_only='true'
  );

  CREATE TABLE IF NOT EXISTS offline_features_author_engagement_{{ spec }} (
    author_id BIGINT,
    event_time TIMESTAMP,
    num_all INT,
    num_favs INT,
    num_reblogs INT,
    num_replies INT,
    num_poll_votes INT,
    num_bookmarks INT,
    num_quotes INT,
    num_has_link INT,
    num_has_photo_link INT,
    num_has_video_link INT,
    num_has_rich_link INT,
    num_has_poll INT,
    num_has_image INT,
    num_has_gifv INT,
    num_has_video INT,
    num_has_audio INT,
    num_has_quote INT,
    avg_text_chars_count FLOAT,
    max_text_chars_count INT,
    min_text_chars_count INT,
    avg_text_uppercase_count FLOAT,
    max_text_uppercase_count INT,
    min_text_uppercase_count INT,
    avg_text_newlines_count FLOAT,
    max_text_newlines_count INT,
    min_text_newlines_count INT,
    avg_text_custom_emojis_count FLOAT,
    max_text_custom_emojis_count INT,
    min_text_custom_emojis_count INT,
    avg_status_fav_count FLOAT,
    max_status_fav_count INT,
    min_status_fav_count INT,
    avg_status_reblogs_count FLOAT,
    max_status_reblogs_count INT,
    min_status_reblogs_count INT,
    avg_status_replies_count FLOAT,
    max_status_replies_count INT,
    min_status_replies_count INT,
    avg_mentions FLOAT,
    avg_tags FLOAT,
    PRIMARY KEY (author_id, event_time)
  ) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='offline_features_author_engagement_{{ spec }}',
    properties.bootstrap.server='{{ bootstrap_server }}',
  ) FORMAT PLAIN ENCODE JSON;
{% endfor %}

-- :down

{% for spec in ['1d', '7d', '60d'] -%}
  DROP VIEW IF EXISTS online_features_author_engagement_{{ spec }};
  DROP SINK IF EXISTS online_features_author_engagement_{{ spec }}_sink;
  DROP TABLE IF EXISTS offline_features_author_engagement_{{ spec }};
{% endfor -%}