
-- :up

CREATE TABLE IF NOT EXISTS invites (
    id BIGINT PRIMARY KEY,
    user_id BIGINT,
    code VARCHAR,
    max_uses INT,
    uses INT,
    autofollow BOOLEAN,
    comment VARCHAR,
    expires_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.invites';

CREATE INDEX IF NOT EXISTS idx_invites_user_id ON invites(user_id);

-- :down

DROP INDEX IF EXISTS idx_invites_user_id;

DROP TABLE IF EXISTS invites CASCADE;
