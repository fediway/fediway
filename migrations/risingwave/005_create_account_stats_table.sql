-- 001_create_source.sql
-- :up
CREATE TABLE account_stats (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    statuses_count BIGINT,
    following_count BIGINT,
    followers_count BIGINT
) FROM pg_source TABLE 'public.account_stats';

-- :down
DROP TABLE IF EXISTS account_stats CASCADE;
