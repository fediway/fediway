
-- :up

{% for window_size, spec in [('7 DAYS', '7d'), ('56 DAYS', '56d')] %}
    CREATE MATERIALIZED VIEW IF NOT EXISTS account_status_{{ spec }} AS
    SELECT
        a.id as account_id,
        MAX(s.created_at)::TIMESTAMP as created_at,
        COUNT(DISTINCT s.id) as statuses_count_{{ spec }},
        {% for column, aggregates in [
          ('reblogs_count', ['sum', 'avg', 'stddev_pop', 'max']), 
          ('replies_count', ['sum', 'avg', 'stddev_pop', 'max']), 
          ('fav_count', ['sum', 'avg', 'stddev_pop', 'max']),
          ('has_image', ['sum', 'avg', 'stddev_pop']), 
          ('has_gifv', ['sum', 'avg', 'stddev_pop']), 
          ('has_video', ['sum', 'avg', 'stddev_pop']), 
          ('has_audio', ['sum', 'avg', 'stddev_pop']),
          ('num_mentions', ['sum', 'avg', 'stddev_pop', 'max']), 
          ('num_tags', ['sum', 'avg', 'stddev_pop', 'max']),
          ('is_reblog', ['sum', 'avg', 'stddev_pop']),
          ('is_reply', ['sum', 'avg', 'stddev_pop']),
        ] %}
          {% for method in aggregates %}
            {{ method }}(m.{{ column }}::INT) as {{ column }}_{{ method }}_{{ spec }}{% if not loop.last %}, {% endif %}
          {% endfor %}{% if not loop.last %}, {% endif %}
        {% endfor %}
    FROM accounts a
    JOIN statuses s ON s.account_id = a.id AND s.created_at >= NOW() - INTERVAL '{{ window_size }}'
    JOIN statuses_meta m ON m.status_id = s.id
    GROUP BY a.id;

    CREATE SINK IF NOT EXISTS account_status_{{ spec }}_sink
    FROM account_status_{{ spec }}
    WITH (
      connector='kafka',
      properties.bootstrap.server='${bootstrap_server}',
      topic='account_status_{{ spec }}',
      primary_key='account_id',
      properties.linger.ms='30000',
    ) FORMAT PLAIN ENCODE JSON (
      force_append_only='true'
    );
{% endfor %}

-- :down

{% for spec in ['7d', '56d'] %}
    DROP SINK IF EXISTS account_status_{{ spec }}_sink;
    DROP VIEW IF EXISTS account_status_{{ spec }};
{% endfor %}