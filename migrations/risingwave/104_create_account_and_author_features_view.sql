
-- :up
{% for group_id, group, interval, interval_name, specs in [
  ('account_id', 'account', '1 HOUR', 'hourly', [(24, '1d'), (6*24, '7d'), (29*24, '30d')]), 
  ('author_id', 'author', '1 HOUR', 'hourly', [(24, '1d'), (6*24, '7d'), (29*24, '30d')]),
  ('account_id, author_id', 'account_author', '1 DAY', 'daily', [(29*24, '30d')]),
] -%}
  CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_all_{{ interval_name }} AS
  SELECT
    window_start, 
    window_end,
    MAX(event_time)::TIMESTAMP as event_time,
    {% for id in group_id.split(',') -%}
      {{ id }}::BIGINT,
    {% endfor %}
    COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count,
    COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count,
    COUNT(*) FILTER (WHERE type = 'reply') AS replies_count,
    SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images,
    SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs,
    SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos,
    SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios,
    SUM(num_mentions) AS num_mentions
  FROM 
    TUMBLE (enriched_status_engagements, event_time, INTERVAL '{{ interval }}')
  GROUP BY {{ group_id }}, window_start, window_end;

  CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_all_features AS
  SELECT
      {% for id in group_id.split(',') -%}
        {{ id }}::BIGINT,
      {% endfor %}
      event_time::TIMESTAMP, 

      {% for intervals, spec in specs %}
        (SUM(num_images) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS num_images_{{ spec }},
        (SUM(num_gifvs) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS num_gifvs_{{ spec }},
        (SUM(num_videos) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS num_videos_{{ spec }},
        (SUM(num_audios) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS num_audios_{{ spec }},
        (SUM(fav_count) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS fav_count_{{ spec }},
        (SUM(reblogs_count) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS reblogs_count_{{ spec }},
        (SUM(replies_count) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS replies_count_{{ spec }}
        {% if not loop.last %},{% endif %}
      {% endfor %}
  FROM {{ group }}_engagement_all_{{ interval_name }};

  CREATE TABLE IF NOT EXISTS offline_fs_{{ group }}_engagement_all_features (
      {% for id in group_id.split(',') -%}
        {{ id }} BIGINT,
      {% endfor %}
      event_time TIMESTAMP, 

      {% for intervals, spec in specs %}
        num_images_{{ spec }} INT,
        num_gifvs_{{ spec }} INT,
        num_videos_{{ spec }} INT,
        num_audios_{{ spec }} INT,
        fav_count_{{ spec }} INT,
        reblogs_count_{{ spec }} INT,
        replies_count_{{ spec }} INT
        {% if not loop.last %},{% endif %}
      {% endfor %}
  ) APPEND ONLY WITH (retention_seconds = 62208000);

  CREATE SINK IF NOT EXISTS offline_fs_{{ group }}_engagement_all_sink
  INTO offline_fs_{{ group }}_engagement_all_features
  FROM {{ group }}_engagement_all_features
  WITH (type = 'append-only', force_append_only='true');

  -- CREATE SINK IF NOT EXISTS {{ group }}_engagement_all_features_sink
  -- FROM {{ group }}_engagement_all_features
  -- WITH (
  --     connector='kafka',
  --     properties.bootstrap.server='${bootstrap_server}',
  --     topic='{{ group }}_engagement_all_features',
  --     primary_key='{{ group_id }},event_time',
  -- ) FORMAT DEBEZIUM ENCODE JSON;

  {% for type in ['favourite', 'reblog', 'reply'] -%}
    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_{{ interval_name }} AS
    SELECT
      window_start, 
      window_end,
      MAX(event_time)::TIMESTAMP as event_time,
      {% for id in group_id.split(',') -%}
        {{ id }}::BIGINT,
      {% endfor %}
      SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images,
      SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs,
      SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos,
      SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios,
      SUM(num_mentions) AS num_mentions
    FROM 
      TUMBLE (enriched_status_engagements, event_time, INTERVAL '{{ interval }}')
    WHERE
      type = '{{ type }}'
    GROUP BY {{ group_id }}, window_start, window_end;

    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_features AS
    SELECT
        {% for id in group_id.split(',') -%}
          {{ id }}::BIGINT,
        {% endfor %}
        event_time::TIMESTAMP, 

        {% for intervals, spec in specs %}
          (SUM(num_images) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS num_images_{{ spec }},
          (SUM(num_gifvs) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS num_gifvs_{{ spec }},
          (SUM(num_videos) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS num_videos_{{ spec }},
          (SUM(num_audios) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS num_audios_{{ spec }}
          {% if not loop.last %},{% endif %}
        {% endfor %}
    FROM {{ group }}_engagement_is_{{ type }}_{{ interval_name }};

    CREATE TABLE IF NOT EXISTS offline_fs_{{ group }}_engagement_is_{{ type }}_features (
        {% for id in group_id.split(',') -%}
          {{ id }} BIGINT,
        {% endfor %}
        event_time TIMESTAMP, 

        {% for intervals, spec in specs %}
          num_images_{{ spec }} INT,
          num_gifvs_{{ spec }} INT,
          num_videos_{{ spec }} INT,
          num_audios_{{ spec }} INT
          {% if not loop.last %},{% endif %}
        {% endfor %}
    ) APPEND ONLY WITH (retention_seconds = 62208000);

    CREATE SINK IF NOT EXISTS offline_fs_{{ group }}_engagement_is_{{ type }}_sink
    INTO offline_fs_{{ group }}_engagement_is_{{ type }}_features
    FROM {{ group }}_engagement_is_{{ type }}_features
    WITH (type = 'append-only', force_append_only='true');

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
    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_has_{{ media }}_{{ interval_name }} AS
    SELECT
      window_start, 
      window_end,
      MAX(event_time)::TIMESTAMP as event_time,
      {% for id in group_id.split(',') -%}
        {{ id }}::BIGINT,
      {% endfor %}
      COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count,
      COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count,
      COUNT(*) FILTER (WHERE type = 'reply') AS replies_count,
      SUM(num_mentions) AS num_mentions
    FROM 
      TUMBLE (enriched_status_engagements, event_time, INTERVAL '{{ interval }}')
    WHERE has_{{ media }}
    GROUP BY {{ group_id }}, window_start, window_end;

    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_has_{{ media }}_features AS
    SELECT
        {% for id in group_id.split(',') -%}
          {{ id }}::BIGINT,
        {% endfor %}
        event_time::TIMESTAMP,  

        {% for intervals, spec in specs %}
          (SUM(fav_count) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS fav_count_{{ spec }},
          (SUM(reblogs_count) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS reblogs_count_{{ spec }},
          (SUM(replies_count) OVER (PARTITION BY {{ group_id }} ORDER BY window_end ROWS BETWEEN {{ intervals }} PRECEDING AND CURRENT ROW))::INT AS replies_count_{{ spec }}
          {% if not loop.last %},{% endif %}
        {% endfor %}
    FROM {{ group }}_engagement_has_{{ media }}_{{ interval_name }};

    CREATE TABLE IF NOT EXISTS offline_fs_{{ group }}_engagement_has_{{ media }}_features (
        {% for id in group_id.split(',') -%}
          {{ id }} BIGINT,
        {% endfor %} 
        event_time TIMESTAMP, 

        {% for intervals, spec in specs %}
          fav_count_{{ spec }} INT,
          reblogs_count_{{ spec }} INT,
          replies_count_{{ spec }} INT
          {% if not loop.last %},{% endif %}
        {% endfor %}
    ) APPEND ONLY WITH (retention_seconds = 62208000);

    CREATE SINK IF NOT EXISTS offline_fs_{{ group }}_engagement_has_{{ media }}_sink
    INTO offline_fs_{{ group }}_engagement_has_{{ media }}_features
    FROM {{ group }}_engagement_has_{{ media }}_features
    WITH (type = 'append-only', force_append_only='true');

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
{% for group, interval_name in [('account', 'hourly'), ('author', 'hourly'), ('account_author', 'daily')] -%}
  DROP VIEW IF EXISTS {{ group }}_engagement_all_{{ interval_name }};
  DROP VIEW IF EXISTS {{ group }}_engagement_all_features;
  DROP TABLE IF EXISTS offline_fs_{{ group }}_engagement_all_features;
  DROP SINK IF EXISTS {{ group }}_engagement_all_sink;

  {% for type in ['favourite', 'reblog', 'reply'] -%}
    DROP VIEW IF EXISTS {{ group }}_engagement_is_{{ type }}_{{ interval_name }};
    DROP VIEW IF EXISTS {{ group }}_engagement_is_{{ type }}_features;
    DROP TABLE IF EXISTS offline_fs_{{ group }}_engagement_is_{{ type }}_features;
    DROP SINK IF EXISTS {{ group }}_engagement_is_{{ type }}_sink;
  {% endfor -%}

  {% for media in ['image', 'gifv', 'video'] -%}
    DROP VIEW IF EXISTS {{ group }}_engagement_has_{{ media }}_{{ interval_name }};
    DROP VIEW IF EXISTS {{ group }}_engagement_has_{{ media }}_features;
    DROP TABLE IF EXISTS offline_fs_{{ group }}_engagement_has_{{ media }}_features;
    DROP SINK IF EXISTS {{ group }}_engagement_has_{{ media }}_sink;
  {% endfor -%}
{% endfor -%}