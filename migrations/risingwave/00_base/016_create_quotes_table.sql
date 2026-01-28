
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

CREATE INDEX IF NOT EXISTS idx_quotes_account_id ON quotes(account_id);
CREATE INDEX IF NOT EXISTS idx_quotes_status_id ON quotes(status_id); 
CREATE INDEX IF NOT EXISTS idx_quotes_quoted_status_id ON quotes(quoted_status_id);
CREATE INDEX IF NOT EXISTS idx_quotes_quoted_account_id ON quotes(quoted_account_id); 

-- :down

DROP TABLE IF EXISTS quotes;
