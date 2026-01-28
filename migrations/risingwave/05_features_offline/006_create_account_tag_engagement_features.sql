
-- :up

{% for window_size, spec in [('24 HOURS', '1d'), ('7 DAYS', '7d'), ('60 DAYS', '60d')] %}
  CREATE TABLE IF NOT EXISTS offline_features_account_tag_engagement_{{ spec }} (
    account_id BIGINT,
    tag_id BIGINT,
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
    PRIMARY KEY (account_id, tag_id, event_time)
  ) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='offline_features_account_tag_engagement_{{ spec }}',
    properties.bootstrap.server='{{ bootstrap_server }}',
  ) FORMAT PLAIN ENCODE JSON;
{% endfor %}

-- :down

{% for spec in ['1d', '7d', '60d'] -%}
  DROP TABLE IF EXISTS offline_features_account_tag_engagement_{{ spec }};
{% endfor -%}
