
-- :up
CREATE TABLE IF NOT EXISTS media_attachments (
    id BIGINT PRIMARY KEY,
    status_id BIGINT,
    account_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    shortcode VARCHAR,
    type INT,
    file_meta JSONB,
    description TEXT,
    scheduled_status_id BIGINT
) FROM pg_source TABLE 'public.media_attachments';

-- :down
DROP TABLE IF EXISTS media_attachments CASCADE;
