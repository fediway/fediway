-- 001_create_source.sql
-- :up
CREATE TABLE statuses_tags (
    status_id BIGINT,
    tag_id BIGINT,
    PRIMARY KEY (status_id, tag_id)
) FROM pg_source TABLE 'public.statuses_tags';

-- :down
DROP TABLE IF EXISTS statuses_tags CASCADE;
