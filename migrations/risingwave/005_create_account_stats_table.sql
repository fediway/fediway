
-- :up
CREATE TABLE IF NOT EXISTS account_stats (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    statuses_count BIGINT,
    following_count BIGINT,
    followers_count BIGINT
) FROM pg_source TABLE 'public.account_stats';

CREATE INDEX idx_account_stats_account_id ON account_stats(account_id);

-- :down
DROP INDEX IF EXISTS idx_account_stats_account_id;
DROP TABLE IF EXISTS account_stats CASCADE;
