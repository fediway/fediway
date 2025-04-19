-- 001_create_source.sql
-- :up
CREATE TABLE accounts (
    id BIGINT PRIMARY KEY,
    username VARCHAR,
    domain VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    note TEXT,
    display_name VARCHAR,
    uri VARCHAR,
    url VARCHAR,
    locked BOOLEAN,
    memorial BOOLEAN,
    actor_type VARCHAR,
    discoverable BOOLEAN,
    also_known_as VARCHAR,
    silenced_at TIMESTAMP,
    suspended_at TIMESTAMP,
    trendable BOOLEAN,
    indexable BOOLEAN,
    attribution_domains VARCHAR
) FROM pg_source TABLE 'public.accounts';
-- CREATE TABLE statuses (*) FROM pg_source TABLE 'public.statuses';
-- CREATE TABLE status_stats (*) FROM pg_source TABLE 'public.status_stats';
-- CREATE TABLE follows (*) FROM pg_source TABLE 'public.follows';
-- CREATE TABLE mentions (*) FROM pg_source TABLE 'public.mentions';
-- CREATE TABLE favourites (*) FROM pg_source TABLE 'public.favourites';
-- CREATE TABLE tags (*) FROM pg_source TABLE 'public.tags';
-- CREATE TABLE statuses_tags (*) FROM pg_source TABLE 'public.statuses_tags';

-- :down
DROP TABLE IF EXISTS accounts;
-- DROP TABLE IF EXISTS statuses;
-- DROP TABLE IF EXISTS status_stats;
-- DROP TABLE IF EXISTS follows;
-- DROP TABLE IF EXISTS mentions;
-- DROP TABLE IF EXISTS favourites;
-- DROP TABLE IF EXISTS tags;
-- DROP TABLE IF EXISTS statuses_tags;