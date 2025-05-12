
-- :up
{% for table, primary_key in [
    ('statuses', 'id'), 
    ('mentions', 'id'), 
    ('follows', 'id'), 
    ('favourites', 'id'), 
    ('statuses_tags', 'status_id,tag_id'),
    ('status_stats', 'id')
] -%}
    CREATE SINK IF NOT EXISTS {{ table }}_sink
    FROM {{ table }}
    WITH (
        connector='kafka',
        properties.bootstrap.server='${bootstrap_server}',
        topic='{{ table }}',
        primary_key='{{ primary_key }}',
    ) FORMAT DEBEZIUM ENCODE JSON;
{% endfor -%}

-- :down
{% for table in ['accounts', 'statuses', 'mentions', 'follows', 'favourites', 'tags', 'statuses_tags', 'status_stats']  %}
    DROP SINK IF EXISTS {{ table }}_sink;
{% endfor -%}