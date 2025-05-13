
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

-- :down
DROP TABLE IF EXISTS statuses CASCADE;
