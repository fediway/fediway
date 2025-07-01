
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

CREATE INDEX IF NOT EXISTS idx_media_attachments_status_id ON media_attachments(status_id);
CREATE INDEX IF NOT EXISTS idx_media_attachments_account_id ON media_attachments(account_id);

-- :down

DROP INDEX IF EXISTS idx_media_attachments_status_id;
DROP INDEX IF EXISTS idx_media_attachments_account_id;

DROP TABLE IF EXISTS media_attachments CASCADE;
