
-- :up
{% for group_id, group, specs in [
  ('account_id', 'account', [('24 HOURS', '1d'), ('7 DAYS', '7d'), ('56 DAYS', '56d')]), 
  ('author_id', 'author', [('24 HOURS', '1d'), ('7 DAYS', '7d'), ('56 DAYS', '56d')]),
  ('account_id,author_id', 'account_author', [('56 DAYS', '56d')]),
] -%}
  {% for window_size, spec in specs %}
    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_all_{{ spec }} AS
    SELECT
      MAX(event_time)::TIMESTAMP as event_time,
      {% for id in group_id.split(',') -%}
        e.{{ id }}::BIGINT,
      {% endfor %}
      COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count_{{ spec }},
      COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count_{{ spec }},
      COUNT(*) FILTER (WHERE type = 'reply') AS replies_count_{{ spec }},
      SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images_{{ spec }},
      SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs_{{ spec }},
      SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos_{{ spec }},
      SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios_{{ spec }},
      SUM(num_mentions) AS num_mentions_{{ spec }}
    FROM enriched_status_engagement_events e
    {% if group == 'account_author' %}
      JOIN users u ON u.account_id = e.account_id
    {% endif %}
    WHERE event_time >= NOW() - INTERVAL '{{ window_size }}'
    GROUP BY {% for id in group_id.split(',') -%} e.{{ id }}{% if not loop.last %}, {% endif %} {% endfor %};
    
    CREATE SINK IF NOT EXISTS {{ group }}_engagement_all_{{ spec }}_sink
    FROM {{ group }}_engagement_all_{{ spec }}
    WITH (
      connector='kafka',
      properties.bootstrap.server='${bootstrap_server}',
      topic='{{ group }}_engagement_all_{{ spec }}',
      primary_key='{{ group_id }}',
      properties.linger.ms='30000',
    ) FORMAT PLAIN ENCODE JSON (
      force_append_only='true'
    );
  {% endfor %}

  {% for type in ['favourite', 'reblog', 'reply'] -%}
    {% for window_size, spec in specs %}
      CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }} AS
      SELECT
        MAX(event_time)::TIMESTAMP as event_time,
        {% for id in group_id.split(',') -%}
          e.{{ id }}::BIGINT,
        {% endfor %}
        SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images_{{ spec }},
        SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs_{{ spec }},
        SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos_{{ spec }},
        SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios_{{ spec }},
        SUM(num_mentions) AS num_mentions_{{ spec }}
      FROM enriched_status_engagement_events e
      {% if group == 'account_author' %}
        JOIN users u ON u.account_id = e.account_id
      {% endif %}
      WHERE type = '{{ type }}' 
        AND event_time >= NOW() - INTERVAL '{{ window_size }}'
      GROUP BY {% for id in group_id.split(',') -%} e.{{ id }}{% if not loop.last %}, {% endif %} {% endfor %};

      CREATE SINK IF NOT EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }}_sink
      FROM {{ group }}_engagement_is_{{ type }}_{{ spec }}
      WITH (
        connector='kafka',
        properties.bootstrap.server='${bootstrap_server}',
        topic='{{ group }}_engagement_is_{{ type }}_{{ spec }}',
        primary_key='{{ group_id }}',
        properties.linger.ms='30000',
      ) FORMAT PLAIN ENCODE JSON (
        force_append_only='true'
      );
    {% endfor %}
  {% endfor %}

  {% for media in ['image', 'gifv', 'video'] -%}
    {% for window_size, spec in specs %}
      CREATE MATERIALIZED VIEW IF NOT EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }} AS
      SELECT
        MAX(event_time)::TIMESTAMP as event_time,
        {% for id in group_id.split(',') -%}
          e.{{ id }}::BIGINT,
        {% endfor %}
        COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count_{{ spec }},
        COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count_{{ spec }},
        COUNT(*) FILTER (WHERE type = 'reply') AS replies_count_{{ spec }},
        SUM(num_mentions) AS num_mentions_{{ spec }}
      FROM enriched_status_engagement_events e
      {% if group == 'account_author' %}
        JOIN users u ON u.account_id = e.account_id
      {% endif %}
      WHERE has_{{ media }}
        AND event_time >= NOW() - INTERVAL '{{ window_size }}'
      GROUP BY {% for id in group_id.split(',') -%} e.{{ id }}{% if not loop.last %}, {% endif %} {% endfor %};

      CREATE SINK IF NOT EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }}_sink
      FROM {{ group }}_engagement_has_{{ media }}_{{ spec }}
      WITH (
        connector='kafka',
        properties.bootstrap.server='${bootstrap_server}',
        topic='{{ group }}_engagement_has_{{ media }}_{{ spec }}',
        primary_key='{{ group_id }}',
        properties.linger.ms='30000',
      ) FORMAT PLAIN ENCODE JSON (
        force_append_only='true'
      );
    {% endfor %}
  {% endfor -%}
{% endfor -%}

-- :down
{% for group, specs in [('account', ['1d', '7d', '56d']), ('author', ['1d', '7d', '56d']), ('account_author', ['56d'])] -%}
  {% for spec in specs -%}
    DROP VIEW IF EXISTS {{ group }}_engagement_all_{{ spec }};
    DROP VIEW IF EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }};
    DROP VIEW IF EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }};

    DROP SINK IF EXISTS {{ group }}_engagement_all_{{ spec }}_sink;
    DROP SINK IF EXISTS {{ group }}_engagement_is_{{ type }}_{{ spec }}_sink;
    DROP SINK IF EXISTS {{ group }}_engagement_has_{{ media }}_{{ spec }}_sink;
  {% endfor -%}
{% endfor -%}