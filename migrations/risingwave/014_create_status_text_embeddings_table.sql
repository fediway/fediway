
-- :up
CREATE TABLE status_text_embeddings (
    status_id BIGINT PRIMARY KEY,
    embedding REAL[],
    created_at TIMESTAMP
) WITH (
    connector = 'kafka',
    topic = 'status_text_embeddings',
    properties.bootstrap.server = '${bootstrap_server}',
) FORMAT PLAIN ENCODE JSON;

-- :down
DROP TABLE IF EXISTS status_text_embeddings CASCADE;
