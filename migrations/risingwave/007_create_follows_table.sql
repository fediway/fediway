
-- :up
CREATE TABLE IF NOT EXISTS follows (
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

CREATE INDEX idx_follows_account_id ON follows(account_id);
CREATE INDEX idx_follows_target_account_id ON follows(target_account_id);

-- :down
DROP INDEX IF EXISTS idx_follows_account_id;
DROP INDEX IF EXISTS idx_follows_target_account_id;
DROP TABLE IF EXISTS follows CASCADE;
