
-- :up

{% for window_size, spec in [('24 HOURS', '1d'), ('7 DAYS', '7d'), ('60 DAYS', '60d')] %}
  CREATE MATERIALIZED VIEW IF NOT EXISTS online_features_account_instance_engagement_{{ spec }} AS
  SELECT
    MAX(event_time)::TIMESTAMP as event_time,
    e.account_id,
    e.target_instance as instance,
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
  AND EXISTS (SELECT 1 FROM users u WHERE u.account_id = e.account_id)
  GROUP BY e.account_id, e.target_instance;

  CREATE SINK IF NOT EXISTS online_features_account_instance_engagement_{{ spec }}_sink
  FROM online_features_account_instance_engagement_{{ spec }}
  WITH (
    connector='kafka',
    properties.bootstrap.server='{{ bootstrap_server }}',
    topic='online_features_account_instance_engagement_{{ spec }}',
    primary_key='account_id,instance',
    properties.linger.ms='10000',
  ) FORMAT PLAIN ENCODE JSON (
    force_append_only='true'
  );
{% endfor %}

-- :down

{% for spec in ['1d', '7d', '60d'] -%}
  DROP SINK IF EXISTS online_features_account_instance_engagement_{{ spec }}_sink;
  DROP VIEW IF EXISTS online_features_account_instance_engagement_{{ spec }};
{% endfor -%}
