
-- :up
{% for table, primary_key in [
    ('accounts', 'id'), 
    ('statuses', 'id'), 
    ('mentions', 'id'), 
    ('follows', 'id'), 
    ('favourites', 'id'), 
    ('tags', 'id'), 
    ('statuses_tags', 'status_id,tag_id')
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
{% for table in ['accounts', 'statuses', 'mentions', 'follows', 'favourites', 'tags', 'statuses_tags']  %}
    DROP SINK IF EXISTS {{ table }}_sink;
{% endfor -%}