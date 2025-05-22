
-- :up

{% for hop_size, window_size, spec in [('1 HOUR', '24 HOURS', '1d'), ('1 DAY', '7 DAYS', '7d'), ('7 DAYS', '56 DAYS', '56d')] %}
    CREATE MATERIALIZED VIEW IF NOT EXISTS account_tag_engagement_all_{{ spec }}_features AS
    SELECT
        window_start, 
        window_end, 
        account_id,
        tag_id,
        MAX(event_time)::TIMESTAMP as event_time,
        COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count_{{ spec }},
        COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count_{{ spec }},
        COUNT(*) FILTER (WHERE type = 'reply') AS replies_count_{{ spec }},
        SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images_{{ spec }},
        SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs_{{ spec }},
        SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos_{{ spec }},
        SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios_{{ spec }}
    FROM 
        HOP (
            enriched_status_engagement_events, 
            event_time, 
            INTERVAL '{{ hop_size }}', 
            INTERVAL '{{ window_size }}'
        ) e
    JOIN statuses_tags st ON e.status_id = st.status_id
    GROUP BY account_id, tag_id, window_start, window_end;

    CREATE MATERIALIZED VIEW IF NOT EXISTS account_tag_engagement_all_{{ spec }} AS
    SELECT *
    FROM account_tag_engagement_all_{{ spec }}_historical
    WHERE window_end >= NOW()
      AND window_end <= NOW() + INTERVAL '{{ hop_size }}';
    
    CREATE SINK IF NOT EXISTS account_tag_engagement_all_{{ spec }}_sink
    FROM account_tag_engagement_all_{{ spec }}
    WITH (
      connector='kafka',
      properties.bootstrap.server='${bootstrap_server}',
      topic='account_tag_engagement_all_{{ spec }}',
      primary_key='{{ group_id }}',
    ) FORMAT PLAIN ENCODE JSON (
      force_append_only='true'
    );
{% endfor %}

-- :down

{% for spec in ['1d', '7d', '56d'] %}
    DROP SINK IF EXISTS account_tag_engagement_all_{{ spec }}_sink;
    DROP VIEW IF EXISTS account_tag_engagement_all_{{ spec }};
    DROP VIEW IF EXISTS account_tag_engagement_all_{{ spec }}_features;
{% endfor %}