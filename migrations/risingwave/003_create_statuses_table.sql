
-- :up
CREATE TABLE IF NOT EXISTS statuses (
    id BIGINT PRIMARY KEY,
    uri VARCHAR,
    text TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    in_reply_to_id BIGINT,
    reblog_of_id BIGINT,
    url VARCHAR,
    sensitive BOOLEAN,
    visibility INT,
    spoiler_text TEXT,
    reply BOOLEAN,
    language VARCHAR,
    conversation_id BIGINT,
    local BOOLEAN,
    account_id BIGINT,
    application_id BIGINT,
    in_reply_to_account_id BIGINT,
    poll_id BIGINT,
    deleted_at TIMESTAMP,
    edited_at TIMESTAMP
) FROM pg_source TABLE 'public.statuses';

CREATE INDEX IF NOT EXISTS idx_statuses_reblog_of_id ON statuses(reblog_of_id);
CREATE INDEX IF NOT EXISTS idx_statuses_in_reply_to_id ON statuses(in_reply_to_id); 
CREATE INDEX IF NOT EXISTS idx_statuses_in_reply_to_account_id ON statuses(in_reply_to_account_id); 

-- :down
DROP INDEX IF EXISTS idx_statuses_reblog_of_id;
DROP INDEX IF EXISTS idx_statuses_in_reply_to_id;
DROP INDEX IF EXISTS idx_statuses_in_reply_to_account_id;
DROP TABLE IF EXISTS statuses CASCADE;
