
-- :up

CREATE TABLE IF NOT EXISTS favourites (
    id BIGINT PRIMARY KEY,
    status_id BIGINT,
    account_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) FROM pg_source TABLE 'public.favourites';

CREATE INDEX IF NOT EXISTS idx_favourites_status_id ON favourites(status_id);
CREATE INDEX IF NOT EXISTS idx_favourites_account_id ON favourites(account_id);

-- :down

DROP INDEX IF EXISTS idx_favourites_status_id;
DROP INDEX IF EXISTS idx_favourites_account_id;

DROP TABLE IF EXISTS favourites CASCADE;
