
-- :up

{% for hop_size, window_size, spec in [('1 HOUR', '24 HOURS', '1d'), ('1 DAY', '7 DAYS', '7d'), ('7 DAYS', '56 DAYS', '56d')] %}
    CREATE MATERIALIZED VIEW IF NOT EXISTS tag_engagement_all_{{ spec }} AS
    SELECT
        tag_id,
        MAX(event_time)::TIMESTAMP as event_time,
        COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count_{{ spec }},
        COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count_{{ spec }},
        COUNT(*) FILTER (WHERE type = 'reply') AS replies_count_{{ spec }},
        SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images_{{ spec }},
        SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs_{{ spec }},
        SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos_{{ spec }},
        SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios_{{ spec }}
    FROM enriched_status_engagement_events e
    JOIN statuses_tags st ON e.status_id = st.status_id
    WHERE event_time >= NOW() - INTERVAL '{{ window_size }}'
    GROUP BY tag_id;
    
    CREATE SINK IF NOT EXISTS tag_engagement_all_{{ spec }}_sink
    FROM tag_engagement_all_{{ spec }}
    WITH (
      connector='kafka',
      properties.bootstrap.server='${bootstrap_server}',
      topic='tag_engagement_all_{{ spec }}',
      primary_key='{{ group_id }}',
      properties.linger.ms='60000',
    ) FORMAT PLAIN ENCODE JSON (
      force_append_only='true'
    );
{% endfor %}

-- :down

{% for spec in ['1d', '7d', '56d'] %}
    DROP SINK IF EXISTS tag_engagement_all_{{ spec }}_sink;
    DROP VIEW IF EXISTS tag_engagement_all_{{ spec }};
{% endfor %}