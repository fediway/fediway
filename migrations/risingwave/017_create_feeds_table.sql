
-- :up
CREATE TABLE IF NOT EXISTS feeds (
    id VARCHAR PRIMARY KEY,
    user_agent VARCHAR,
    ip VARCHAR,
    name VARCHAR,
    entity VARCHAR,
    account_id BIGINT,
    created_at TIMESTAMP,
);

-- :down
DROP TABLE IF EXISTS feeds CASCADE;