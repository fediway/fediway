
-- :up

CREATE TABLE IF NOT EXISTS bookmarks (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    status_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.bookmarks';

CREATE INDEX IF NOT EXISTS idx_bookmarks_account_id ON bookmarks(account_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_target_account_id ON bookmarks(status_id); 

-- :down

DROP INDEX IF EXISTS idx_bookmarks_account_id;
DROP INDEX IF EXISTS idx_bookmarks_status_id;

DROP TABLE IF EXISTS bookmarks;