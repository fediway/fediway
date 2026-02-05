
-- :up

CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT PRIMARY KEY,
    uri VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.conversations';

CREATE TABLE IF NOT EXISTS conversation_mutes (
    id BIGINT PRIMARY KEY,
    conversation_id BIGINT,
    account_id BIGINT,
) FROM pg_source TABLE 'public.conversation_mutes';

CREATE INDEX IF NOT EXISTS idx_conversation_mutes_account_id ON conversation_mutes(account_id);
CREATE INDEX IF NOT EXISTS idx_conversation_mutes_target_conversation_id ON conversation_mutes(conversation_id); 

-- :down

DROP INDEX IF EXISTS idx_conversation_mutes_account_id;
DROP INDEX IF EXISTS idx_conversation_mutes_target_conversation_id;

DROP TABLE IF EXISTS conversation_mutes;
DROP TABLE IF EXISTS conversations;