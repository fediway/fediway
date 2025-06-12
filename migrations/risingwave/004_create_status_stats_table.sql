
-- :up
CREATE TABLE IF NOT EXISTS status_stats (
    id BIGINT PRIMARY KEY,
    status_id BIGINT,
    reblogs_count BIGINT,
    favourites_count BIGINT,
    replies_count BIGINT
) FROM pg_source TABLE 'public.status_stats';

CREATE INDEX IF NOT EXISTS idx_status_id_status_id ON status_stats(status_id);

-- :down
DROP INDEX IF EXISTS idx_status_id_status_id;
DROP TABLE IF EXISTS status_stats CASCADE;
