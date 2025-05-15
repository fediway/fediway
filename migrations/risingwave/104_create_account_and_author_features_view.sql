
-- :up
{% for group_id, group, specs in [
  ('account_id', 'account', [('1 HOUR', '24 HOURS', '1d'), ('1 DAY', '7 DAYS', '7d'), ('1 DAY', '30 DAYS', '30d')]), 
  ('author_id', 'author', [('1 HOUR', '24 HOURS', '1d'), ('1 DAY', '7 DAYS', '7d'), ('1 DAY', '30 DAYS', '30d')]),
  ('account_id,author_id', 'account_author', [('1 DAY', '30 DAYS', '30d')]),
] -%}
  {% for hop_size, window_size, spec in specs %}
    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_all_{{ spec }}_features AS
    SELECT
      window_start, 
      window_end,
      MAX(event_time)::TIMESTAMP as event_time,
      {% for id in group_id.split(',') -%}
        {{ id }}::BIGINT,
      {% endfor %}
      COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count_{{ spec }},
      COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count_{{ spec }},
      COUNT(*) FILTER (WHERE type = 'reply') AS replies_count_{{ spec }},
      SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images_{{ spec }},
      SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs_{{ spec }},
      SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos_{{ spec }},
      SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios_{{ spec }},
      SUM(num_mentions) AS num_mentions_{{ spec }}
    FROM 
      HOP (enriched_status_engagements, event_time, INTERVAL '{{ hop_size }}', INTERVAL '{{ window_size }}')
    GROUP BY {{ group_id }}, window_start, window_end;

    -- CREATE TABLE IF NOT EXISTS offline_fs_{{ group }}_engagement_all_features_{{ spec }} (
    --   {% for id in group_id.split(',') -%}
    --     {{ id }} BIGINT,
    --   {% endfor %}
    --   event_time TIMESTAMP, 

    --   {% for _, _, spec in specs %}
    --     num_images_{{ spec }} INT,
    --     num_gifvs_{{ spec }} INT,
    --     num_videos_{{ spec }} INT,
    --     num_audios_{{ spec }} INT,
    --     fav_count_{{ spec }} INT,
    --     reblogs_count_{{ spec }} INT,
    --     replies_count_{{ spec }} INT
    --     {% if not loop.last %},{% endif %}
    --   {% endfor %}
    -- ) APPEND ONLY WITH (retention_seconds = 62208000);

    -- CREATE SINK IF NOT EXISTS offline_fs_{{ group }}_engagement_all_sink
    -- INTO offline_fs_{{ group }}_engagement_all_features
    -- FROM {{ group }}_engagement_all_features
    -- WITH (type = 'append-only', force_append_only='true');
  {% endfor %}

  -- CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_all_features AS
  -- SELECT
  --     {% for id in group_id.split(',') -%}
  --       a.{{ id }}::BIGINT,
  --     {% endfor %}
  --     a.event_time::TIMESTAMP,
  --     {% for hop_size, window_size, spec in specs %}
  --       num_images_{{ spec }},
  --       num_gifvs_{{ spec }},
  --       num_videos_{{ spec }},
  --       num_audios_{{ spec }},
  --       fav_count_{{ spec }},
  --       reblogs_count_{{ spec }},
  --       replies_count_{{ spec }}{% if not loop.last %},{% endif %}
  --     {% endfor %}
  -- {% for _, _, spec in specs %}
  --   {% if loop.first %}
  --     FROM {{ group }}_engagement_all_features_{{ spec }} a
  --   {% else %}
  --     LEFT JOIN {{ group }}_engagement_all_features_{{ spec }} i{{ spec }}
  --     ON a.event_time = i{{ spec }}.event_time
  --     {% for id in group_id.split(',') -%}
  --       AND a.{{ id }} = i{{ spec }}.{{ id }}
  --     {% endfor %}
  --   {% endif %}
  -- {% endfor %};

  -- CREATE SINK IF NOT EXISTS {{ group }}_engagement_all_features_sink
  -- FROM {{ group }}_engagement_all_features
  -- WITH (
  --     connector='kafka',
  --     properties.bootstrap.server='${bootstrap_server}',
  --     topic='{{ group }}_engagement_all_features',
  --     primary_key='{{ group_id }},event_time',
  -- ) FORMAT DEBEZIUM ENCODE JSON;

  {% for type in ['favourite', 'reblog', 'reply'] -%}
    {% for hop_size, window_size, spec in specs %}
      CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }}_features AS
      SELECT
        window_start, 
        window_end,
        MAX(event_time)::TIMESTAMP as event_time,
        {% for id in group_id.split(',') -%}
          {{ id }}::BIGINT,
        {% endfor %}
        SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images_{{ spec }},
        SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs_{{ spec }},
        SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos_{{ spec }},
        SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios_{{ spec }},
        SUM(num_mentions) AS num_mentions_{{ spec }}
      FROM 
        HOP (enriched_status_engagements, event_time, INTERVAL '{{ hop_size }}', INTERVAL '{{ window_size }}')
      WHERE
        type = '{{ type }}'
      GROUP BY {{ group_id }}, window_start, window_end;
    {% endfor %}

    -- CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_features AS
    -- SELECT
    --     {% for id in group_id.split(',') -%}
    --       a.{{ id }}::BIGINT,
    --     {% endfor %}
    --     a.event_time::TIMESTAMP,
    --     {% for _, _, spec in specs %}
    --       num_images_{{ spec }},
    --       num_gifvs_{{ spec }},
    --       num_videos_{{ spec }},
    --       num_audios_{{ spec }}{% if not loop.last %},{% endif %}
    --     {% endfor %}    
    -- {% for _, _, spec in specs %}
    --   {% if loop.first %}
    --     FROM {{ group }}_engagement_is_{{ type }}_features_{{ spec }} a
    --   {% else %}
    --     LEFT JOIN {{ group }}_engagement_is_{{ type }}_features_{{ spec }} i{{ spec }}
    --     ON a.window_end = i{{ spec }}.window_end
    --     {% for id in group_id.split(',') -%}
    --       AND a.{{ id }} = i{{ spec }}.{{ id }}
    --     {% endfor %}
    --   {% endif %}
    -- {% endfor %};

    -- CREATE TABLE IF NOT EXISTS offline_fs_{{ group }}_engagement_is_{{ type }}_features (
    --     {% for id in group_id.split(',') -%}
    --       {{ id }} BIGINT,
    --     {% endfor %}
    --     event_time TIMESTAMP, 

    --     {% for _, _, spec in specs %}
    --       num_images_{{ spec }} INT,
    --       num_gifvs_{{ spec }} INT,
    --       num_videos_{{ spec }} INT,
    --       num_audios_{{ spec }} INT
    --       {% if not loop.last %},{% endif %}
    --     {% endfor %}
    -- ) APPEND ONLY WITH (retention_seconds = 62208000);

    -- CREATE SINK IF NOT EXISTS offline_fs_{{ group }}_engagement_is_{{ type }}_sink
    -- INTO offline_fs_{{ group }}_engagement_is_{{ type }}_features
    -- FROM {{ group }}_engagement_is_{{ type }}_features
    -- WITH (type = 'append-only', force_append_only='true');

    -- TODO: Add kafka sink for online feature store (but only latest by event_time and append only!)
    -- CREATE SINK IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_features_sink
    -- FROM {{ group }}_engagement_is_{{ type }}_features
    -- WITH (
    --     connector='kafka',
    --     properties.bootstrap.server='${bootstrap_server}',
    --     topic='{{ group }}_engagement_is_{{ type }}_features',
    --     primary_key='{{ group_id }},event_time',
    -- ) FORMAT DEBEZIUM ENCODE JSON;
  {% endfor %}

  {% for media in ['image', 'gifv', 'video'] -%}
    {% for hop_size, window_size, spec in specs %}
      CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }}_features AS
      SELECT
        window_start, 
        window_end,
        MAX(event_time)::TIMESTAMP as event_time,
        {% for id in group_id.split(',') -%}
          {{ id }}::BIGINT,
        {% endfor %}
        COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count_{{ spec }},
        COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count_{{ spec }},
        COUNT(*) FILTER (WHERE type = 'reply') AS replies_count_{{ spec }},
        SUM(num_mentions) AS num_mentions_{{ spec }}
      FROM 
        HOP (enriched_status_engagements, event_time, INTERVAL '{{ hop_size }}', INTERVAL '{{ window_size }}')
      WHERE has_{{ media }}
      GROUP BY {{ group_id }}, window_start, window_end;
    {% endfor %}

    -- CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_has_{{ type }}_features AS
    -- SELECT
    --     {% for id in group_id.split(',') -%}
    --       a.{{ id }}::BIGINT,
    --     {% endfor %}
    --     a.event_time::TIMESTAMP,
    --     {% for _, _, spec in specs %}
    --       i{{ spec }}.fav_count_{{ spec }},
    --       i{{ spec }}.reblogs_count_{{ spec }},
    --       i{{ spec }}.replies_count_{{ spec }}{% if not loop.last %},{% endif %}
    --     {% endfor %}    
    -- {% for _, _, spec in specs %}
    --   {% if loop.first %}
    --     FROM {{ group }}_engagement_has_{{ media }}_features_{{ spec }} a
    --   {% else %}
    --     LEFT JOIN {{ group }}_engagement_has_{{ media }}_features_{{ spec }} i{{ spec }}
    --     ON a.window_end = i{{ spec }}.window_end
    --     {% for id in group_id.split(',') -%}
    --       AND a.{{ id }} = i{{ spec }}.{{ id }}
    --     {% endfor %}
    --   {% endif %}
    -- {% endfor %};

    -- CREATE TABLE IF NOT EXISTS offline_fs_{{ group }}_engagement_has_{{ media }}_features (
    --     {% for id in group_id.split(',') -%}
    --       {{ id }} BIGINT,
    --     {% endfor %} 
    --     event_time TIMESTAMP, 

    --     {% for _, _, spec in specs %}
    --       fav_count_{{ spec }} INT,
    --       reblogs_count_{{ spec }} INT,
    --       replies_count_{{ spec }} INT
    --       {% if not loop.last %},{% endif %}
    --     {% endfor %}
    -- ) APPEND ONLY WITH (retention_seconds = 62208000);

    -- CREATE SINK IF NOT EXISTS offline_fs_{{ group }}_engagement_has_{{ media }}_sink
    -- INTO offline_fs_{{ group }}_engagement_has_{{ media }}_features
    -- FROM {{ group }}_engagement_has_{{ media }}_features
    -- WITH (type = 'append-only', force_append_only='true');

    -- CREATE SINK IF NOT EXISTS {{ group }}_engagement_has_{{ media }}_features_sink
    -- FROM {{ group }}_engagement_has_{{ media }}_features
    -- WITH (
    --     connector='kafka',
    --     properties.bootstrap.server='${bootstrap_server}',
    --     topic='{{ group }}_engagement_has_{{ media }}_features',
    --     primary_key='{{ group_id }},event_time',
    -- ) FORMAT DEBEZIUM ENCODE JSON;
  {% endfor -%}
{% endfor -%}

-- :down
{% for group, specs in [('account', ['1d', '7d', '30d']), ('author', ['1d', '7d', '30d']), ('account_author', ['30d'])] -%}
  {% for spec in specs -%}
    DROP VIEW IF EXISTS {{ group }}_engagement_all_{{ spec }}_features;
    DROP VIEW IF EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }}_features;
    DROP VIEW IF EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }}_features;
  {% endfor -%}
{% endfor -%}