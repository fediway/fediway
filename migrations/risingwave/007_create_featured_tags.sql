
-- :up

CREATE TABLE IF NOT EXISTS featured_tags (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    tag_id BIGINT,
    last_status_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.featured_tags';

CREATE INDEX IF NOT EXISTS idx_featured_tags_account_id ON featured_tags(account_id);
CREATE INDEX IF NOT EXISTS idx_featured_tags_tag_id ON featured_tags(tag_id);

-- :down

DROP INDEX IF EXISTS idx_featured_tags_account_id;
DROP INDEX IF EXISTS idx_featured_tags_tag_id;

DROP TABLE IF EXISTS featured_tags CASCADE;
