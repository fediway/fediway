-- 001_create_source.sql
-- :up
CREATE TABLE follows (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    target_account_id BIGINT,
    show_reblogs BOOLEAN,
    notify BOOLEAN,
    uri varchar,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    languages VARCHAR[]
) FROM pg_source TABLE 'public.follows';

-- :down
DROP TABLE IF EXISTS follows;
