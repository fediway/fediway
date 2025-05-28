
-- :up
CREATE SINK IF NOT EXISTS status_texts_sink AS
SELECT
    s.id as status_id,
    s.text as text,
    s.language as language
FROM statuses s
WHERE 
    s.reblog_of_id IS NULL
AND s.text IS NOT NULL
WITH (
    connector='kafka',
    properties.bootstrap.server='${bootstrap_server}',
    topic='status_texts',
    primary_key='status_id',
) FORMAT PLAIN ENCODE JSON (
    force_append_only='true'
);

-- :down
DROP SINK IF EXISTS status_texts_sink;