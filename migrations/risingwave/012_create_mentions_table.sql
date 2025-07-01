
-- :up

CREATE TABLE IF NOT EXISTS mentions (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    status_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    silent BOOLEAN
) FROM pg_source TABLE 'public.mentions';

CREATE INDEX IF NOT EXISTS idx_mentions_account_id ON mentions(account_id);
CREATE INDEX IF NOT EXISTS idx_mentions_status_id ON mentions(status_id);

-- :down

DROP INDEX IF EXISTS idx_mentions_account_id;
DROP INDEX IF EXISTS idx_mentions_status_id;

DROP TABLE IF EXISTS mentions CASCADE;
