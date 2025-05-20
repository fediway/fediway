
-- :up

{% for hop_size, window_size, spec in [('1 HOUR', '24 HOURS', '1d'), ('1 DAY', '7 DAYS', '7d'), ('1 DAY', '60 DAYS', '60d')] %}
    CREATE MATERIALIZED VIEW IF NOT EXISTS combined_status_tag_engagement_all_{{ spec }}_features AS
    SELECT
        window_start, 
        window_end, 
        status_id,
        MAX(event_time)::TIMESTAMP as event_time,
        {% for feature in ['fav_count', 'reblogs_count', 'replies_count', 'num_images', 'num_gifvs', 'num_videos', 'num_audios'] %}
            MAX({{ feature }}_{{ spec }}) as max_{{ feature }}_{{ spec }},
            SUM({{ feature }}_{{ spec }}) as sum_{{ feature }}_{{ spec }},
            AVG({{ feature }}_{{ spec }}) as avg_{{ feature }}_{{ spec }}{% if not loop.last %},{% endif %}
        {% endfor %}
    FROM tag_engagement_all_{{ spec }}_features f
    JOIN statuses_tags st ON f.tag_id = st.tag_id
    GROUP BY status_id, window_start, window_end;
{% endfor %}

-- :down

{% for spec in ['1d', '7d', '60d'] %}
    DROP VIEW IF EXISTS combined_status_tag_engagement_all_{{ spec }}_features;
{% endfor %}