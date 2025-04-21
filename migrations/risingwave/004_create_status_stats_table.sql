
-- :up
CREATE TABLE status_stats (
    id BIGINT PRIMARY KEY,
    status_id BIGINT,
    reblogs_count BIGINT,
    favourites_count BIGINT,
    replies_count BIGINT
) FROM pg_source TABLE 'public.status_stats';

-- :down
DROP TABLE IF EXISTS status_stats CASCADE;
