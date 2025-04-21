-- 001_create_source.sql
-- :up
CREATE MATERIALIZED VIEW status_texts AS
SELECT
    s.id as status_id,
    s.text as text,
    s.language as language
FROM statuses s
WHERE 
    s.reblog_of_id IS NULL
AND s.in_reply_to_id IS NULL
AND s.text IS NOT NULL;

CREATE SINK IF NOT EXISTS status_texts_sink
FROM status_texts
WITH (
    connector='kafka',
    properties.bootstrap.server='${bootstrap_server}',
    topic='status_texts',
    primary_key='status_id',
) FORMAT DEBEZIUM ENCODE JSON;

-- :down
DROP VIEW IF EXISTS status_texts;
DROP SINK IF EXISTS status_texts_sink;