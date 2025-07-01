
-- :up

CREATE TABLE IF NOT EXISTS tags (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    display_name VARCHAR,
    usable BOOLEAN,
    listable BOOLEAN,
    trendable BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.tags';

CREATE TABLE IF NOT EXISTS tag_follows (
    id BIGINT PRIMARY KEY,
    tag_id BIGINT,
    account_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.tag_follows';

CREATE INDEX IF NOT EXISTS idx_tag_follows_account_id ON tag_follows(tag_id);
CREATE INDEX IF NOT EXISTS idx_tag_follows_target_account_id ON tag_follows(account_id);

-- :down

DROP INDEX IF EXISTS idx_tag_follows_account_id;
DROP INDEX IF EXISTS idx_tag_follows_target_account_id;

DROP TABLE IF EXISTS tag_follows CASCADE;
DROP TABLE IF EXISTS tags CASCADE;
