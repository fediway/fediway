
-- :up

CREATE TABLE IF NOT EXISTS mutes (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    target_account_id BIGINT,
    hide_notifications BOOLEAN,
    expires_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.mutes';

CREATE INDEX IF NOT EXISTS idx_mutes_account_id ON mutes(account_id);
CREATE INDEX IF NOT EXISTS idx_mutes_target_account_id ON mutes(target_account_id);
CREATE INDEX IF NOT EXISTS idx_mutes_expires_at ON mutes(expires_at);

-- :down

DROP INDEX IF EXISTS idx_mutes_account_id;
DROP INDEX IF EXISTS idx_mutes_target_account_id;
DROP INDEX IF EXISTS idx_mutes_expires_at;

DROP TABLE IF EXISTS mutes CASCADE;
