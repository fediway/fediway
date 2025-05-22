
-- :up
CREATE TABLE IF NOT EXISTS statuses_tags (
    status_id BIGINT,
    tag_id BIGINT,
    PRIMARY KEY (status_id, tag_id)
) FROM pg_source TABLE 'public.statuses_tags';

CREATE INDEX idx_statuses_tags_status_id ON statuses_tags(status_id);
CREATE INDEX idx_statuses_tags_tag_id ON statuses_tags(tag_id);

-- :down
DROP INDEX IF EXISTS idx_statuses_tags_status_id;
DROP INDEX IF EXISTS idx_statuses_tags_tag_id;
DROP TABLE IF EXISTS statuses_tags CASCADE;
