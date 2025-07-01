
-- :up

CREATE TABLE IF NOT EXISTS blocks (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    target_account_id BIGINT,
    uri VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.blocks';

CREATE INDEX IF NOT EXISTS idx_blocks_account_id ON blocks(account_id);
CREATE INDEX IF NOT EXISTS idx_blocks_target_account_id ON blocks(target_account_id); 

-- :down

DROP INDEX IF EXISTS idx_blocks_account_id;
DROP INDEX IF EXISTS idx_blocks_target_account_id;

DROP TABLE IF EXISTS blocks;