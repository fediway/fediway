
-- :up
CREATE TABLE tags (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    display_name VARCHAR,
    usable BOOLEAN,
    listable BOOLEAN,
    trendable BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.tags';

-- :down
DROP TABLE IF EXISTS tags CASCADE;
