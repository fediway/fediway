
-- :up
CREATE TABLE IF NOT EXISTS mentions (
    id BIGINT PRIMARY KEY,
    status_id BIGINT,
    account_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.mentions';

-- :down
DROP TABLE IF EXISTS mentions CASCADE;
