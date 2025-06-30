
-- :up

{% for window_size, spec in [('24 HOURS', '1d'), ('7 DAYS', '7d'), ('60 DAYS', '60d')] %}
    CREATE MATERIALIZED VIEW IF NOT EXISTS online_features_tag_engagement_all_{{ spec }} AS
    SELECT
        tag_id,
        MAX(event_time)::TIMESTAMP as event_time,
        COUNT(DISTINCT e.account_id) AS num_engagers,
        COUNT(DISTINCT e.author_id) AS num_authors,
        COUNT(DISTINCT e.status_id) AS num_statuses,
        COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count,
        COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count,
        COUNT(*) FILTER (WHERE type = 'reply') AS replies_count,
        SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images,
        SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs,
        SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos,
        SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios
    FROM enriched_status_engagement_events e
    JOIN statuses_tags st ON e.status_id = st.status_id
    WHERE event_time >= NOW() - INTERVAL '{{ window_size }}'
    GROUP BY tag_id;
    
    CREATE SINK IF NOT EXISTS tag_engagement_all_{{ spec }}_sink
    FROM online_features_tag_engagement_all_{{ spec }}
    WITH (
      connector='kafka',
      topic='online_features_tag_engagement_all_{{ spec }}',
      primary_key='{{ group_id }}',
      properties.bootstrap.server='{{ bootstrap_server }}',
      properties.linger.ms='60000',
    ) FORMAT PLAIN ENCODE JSON (
      force_append_only='true'
    );

    CREATE TABLE IF NOT EXISTS offline_features_tag_engagement_all_{{ spec }} (
      tag_id BIGINT,
      event_time TIMESTAMP,
      num_engagers INT,
      num_authors INT,
      num_statuses INT,
      fav_count INT,
      reblogs_count INT,
      replies_count INT,
      num_images INT,
      num_gifvs INT,
      num_videos INT,
      num_audios INT,
      PRIMARY KEY (tag_id, event_time)
    ) APPEND ONLY ON CONFLICT IGNORE WITH (
      connector='kafka',
      topic='offline_features_tag_engagement_all_{{ spec }}',
      properties.bootstrap.server='{{ bootstrap_server }}',
    ) FORMAT PLAIN ENCODE JSON;

{% endfor %}

-- :down

{% for spec in ['1d', '7d', '56d'] %}
    DROP SINK IF EXISTS tag_engagement_all_{{ spec }}_sink;
    DROP VIEW IF EXISTS tag_engagement_all_{{ spec }};
    DROP TABLE IF EXISTS offline_features_tag_engagement_all_{{ spec }};
{% endfor %}