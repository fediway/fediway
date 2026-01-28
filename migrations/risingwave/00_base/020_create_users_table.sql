
-- :up

CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    email VARCHAR,
    locale VARCHAR,
    chosen_languages VARCHAR[],
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    disabled BOOLEAN,
    approved BOOLEAN
) FROM pg_source TABLE 'public.users';

CREATE INDEX IF NOT EXISTS idx_users_account_id ON users(account_id);

-- :down
DROP INDEX IF EXISTS idx_users_account_id;
DROP TABLE IF EXISTS users CASCADE;
