-- 001_create_source.sql
-- :up
CREATE TABLE accounts (
    id BIGINT PRIMARY KEY,
    username VARCHAR,
    domain VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    note TEXT,
    display_name VARCHAR,
    uri VARCHAR,
    url VARCHAR,
    locked BOOLEAN,
    memorial BOOLEAN,
    actor_type VARCHAR,
    discoverable BOOLEAN,
    also_known_as VARCHAR,
    silenced_at TIMESTAMP,
    suspended_at TIMESTAMP,
    trendable BOOLEAN,
    indexable BOOLEAN,
    attribution_domains VARCHAR
) FROM pg_source TABLE 'public.accounts';

-- :down
DROP TABLE IF EXISTS accounts CASCADE;