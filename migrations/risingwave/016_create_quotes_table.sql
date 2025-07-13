
-- :up

CREATE TABLE IF NOT EXISTS quotes (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    status_id BIGINT,
    quoted_status_id BIGINT,
    quoted_account_id BIGINT,
    state INT, -- pending: 0, accepted: 1, rejected: 2, revoked: 3
    approval_uri VARCHAR,
    activity_uri VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    legacy BOOLEAN
) FROM pg_source TABLE 'public.quotes';

-- :down

DROP TABLE IF EXISTS quotes;
