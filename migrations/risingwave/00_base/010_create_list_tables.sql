
-- :up

CREATE TABLE IF NOT EXISTS lists (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    title VARCHAR,
    replies_policy INT,
    exclusive BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.lists';

CREATE INDEX IF NOT EXISTS idx_lists_account_id ON lists(account_id);

CREATE TABLE IF NOT EXISTS list_accounts (
    id BIGINT PRIMARY KEY,
    list_id BIGINT,
    account_id BIGINT,
    follow_id BIGINT,
    follow_request_id BIGINT
) FROM pg_source TABLE 'public.list_accounts';

CREATE INDEX IF NOT EXISTS idx_list_accounts_list_id ON list_accounts(list_id);
CREATE INDEX IF NOT EXISTS idx_list_accounts_account_id ON list_accounts(account_id);

-- :down

DROP INDEX IF EXISTS idx_lists_account_id;
DROP INDEX IF EXISTS idx_list_accounts_list_id;
DROP INDEX IF EXISTS idx_list_accounts_account_id;

DROP TABLE IF EXISTS list_accounts CASCADE;
DROP TABLE IF EXISTS lists CASCADE;
