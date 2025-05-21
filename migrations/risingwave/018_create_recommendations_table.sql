
-- :up
CREATE TABLE IF NOT EXISTS recommendations (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    entity VARCHAR,
    entity_id BIGINT,
    score REAL,
    created_at TIMESTAMP
)

-- :down
DROP TABLE IF EXISTS recommendations CASCADE;