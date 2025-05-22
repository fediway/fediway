
-- :up
{% for group_id, group, specs in [
  ('account_id', 'account', [('1 HOUR', '24 HOURS', '1d', '30 DAYS'), ('1 DAY', '7 DAYS', '7d', '3 MONTHS'), ('7 DAYS', '56 DAYS', '56d', '6 MONTHS')]), 
  ('author_id', 'author', [('1 HOUR', '24 HOURS', '1d', '30 DAYS'), ('1 DAY', '7 DAYS', '7d', '3 MONTHS'), ('7 DAYS', '56 DAYS', '56d', '6 MONTHS')]),
  ('account_id,author_id', 'account_author', [('7 DAYS', '56 DAYS', '56d', '6 MONTHS')]),
] -%}
  {% for hop_size, window_size, spec, max_age in specs %}
    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_all_{{ spec }}_historical AS
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
      HOP (enriched_status_engagement_events, event_time, INTERVAL '{{ hop_size }}', INTERVAL '{{ window_size }}')
    GROUP BY {{ group_id }}, window_start, window_end;

    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_all_{{ spec }} AS
    SELECT *
    FROM {{ group }}_engagement_all_{{ spec }}_historical
    WHERE window_end >= NOW()
      AND window_end <= NOW() + INTERVAL '{{ hop_size }}';
    
    CREATE SINK IF NOT EXISTS {{ group }}_engagement_all_{{ spec }}_sink
    FROM {{ group }}_engagement_all_{{ spec }}
    WITH (
      connector='kafka',
      properties.bootstrap.server='${bootstrap_server}',
      topic='{{ group }}_engagement_all_{{ spec }}',
      primary_key='{{ group_id }}',
    ) FORMAT PLAIN ENCODE JSON (
      force_append_only='true'
    );
  {% endfor %}

  {% for type in ['favourite', 'reblog', 'reply'] -%}
    {% for hop_size, window_size, spec, max_age in specs %}
      CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }}_historical AS
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
        HOP (enriched_status_engagement_events, event_time, INTERVAL '{{ hop_size }}', INTERVAL '{{ window_size }}')
      WHERE type = '{{ type }}'
        AND event_time >= NOW() - INTERVAL '{{ max_age }}'
      GROUP BY {{ group_id }}, window_start, window_end;

      CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }} AS
      SELECT *
      FROM {{ group }}_engagement_is_{{ type }}_{{ spec }}_historical
      WHERE window_end > NOW() - INTERVAL '{{ hop_size }}';

      CREATE SINK IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }}_sink
      FROM {{ group }}_engagement_is_{{ type }}_{{ spec }}
      WITH (
        connector='kafka',
        properties.bootstrap.server='${bootstrap_server}',
        topic='{{ group }}_engagement_all_{{ spec }}',
        primary_key='{{ group_id }}',
      ) FORMAT PLAIN ENCODE JSON (
        force_append_only='true'
      );
    {% endfor %}
  {% endfor %}

  {% for media in ['image', 'gifv', 'video'] -%}
    {% for hop_size, window_size, spec, max_age in specs %}
      CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }}_historical AS
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
        HOP (enriched_status_engagement_events, event_time, INTERVAL '{{ hop_size }}', INTERVAL '{{ window_size }}')
      WHERE has_{{ media }}
      GROUP BY {{ group_id }}, window_start, window_end;

      CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }} AS
      SELECT *
      FROM {{ group }}_engagement_has_{{ media }}_{{ spec }}_historical
      WHERE window_end > NOW() - INTERVAL '{{ hop_size }}';

      CREATE SINK IF NOT EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }}_sink
      FROM {{ group }}_engagement_has_{{ media }}_{{ spec }}
      WITH (
        connector='kafka',
        properties.bootstrap.server='${bootstrap_server}',
        topic='{{ group }}_engagement_all_{{ spec }}',
        primary_key='{{ group_id }}',
      ) FORMAT PLAIN ENCODE JSON (
        force_append_only='true'
      );
    {% endfor %}
  {% endfor -%}
{% endfor -%}

-- :down
{% for group, specs in [('account', ['1d', '7d', '56d']), ('author', ['1d', '7d', '56d']), ('account_author', ['56d'])] -%}
  {% for spec in specs -%}
    DROP VIEW IF EXISTS {{ group }}_engagement_all_{{ spec }}_historical;
    DROP VIEW IF EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }}_historical;
    DROP VIEW IF EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }}_historical;

    DROP VIEW IF EXISTS {{ group }}_engagement_all_{{ spec }};
    DROP VIEW IF EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }};
    DROP VIEW IF EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }};

    DROP SINK IF EXISTS {{ group }}_engagement_all_{{ spec }}_sink;
    DROP SINK IF EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }}_sink;
    DROP SINK IF EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }}_sink;
  {% endfor -%}
{% endfor -%}