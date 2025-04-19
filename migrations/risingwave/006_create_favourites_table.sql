-- 001_create_source.sql
-- :up
CREATE TABLE favourites (
    id BIGINT PRIMARY KEY,
    status_id BIGINT,
    account_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) FROM pg_source TABLE 'public.favourites';

-- :down
DROP TABLE IF EXISTS favourites;
