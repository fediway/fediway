
-- :up
CREATE TABLE IF NOT EXISTS follows (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    target_account_id BIGINT,
    show_reblogs BOOLEAN,
    notify BOOLEAN,
    uri varchar,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    languages VARCHAR[]
) FROM pg_source TABLE 'public.follows';

CREATE INDEX IF NOT EXISTS idx_follows_account_id ON follows(account_id);
CREATE INDEX IF NOT EXISTS idx_follows_target_account_id ON follows(target_account_id);

CREATE TABLE IF NOT EXISTS follow_recommendation_mutes (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    target_account_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.follow_recommendation_mutes';

CREATE INDEX IF NOT EXISTS idx_follow_recommendation_mutes_account_id ON follow_recommendation_mutes(account_id);
CREATE INDEX IF NOT EXISTS idx_follow_recommendation_mutes_target_account_id ON follow_recommendation_mutes(target_account_id);

CREATE TABLE IF NOT EXISTS follow_recommendation_suppressions (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.follow_recommendation_suppressions';

CREATE INDEX IF NOT EXISTS idx_follow_recommendation_suppressions_mutes_account_id ON follow_recommendation_suppressions(account_id);

CREATE TABLE IF NOT EXISTS follow_requests (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    target_account_id BIGINT,
    show_reblogs BOOLEAN,
    uri VARCHAR,
    notify BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.follow_requests';

CREATE INDEX IF NOT EXISTS idx_follow_requests_account_id ON follow_requests(account_id);
CREATE INDEX IF NOT EXISTS idx_follow_requests_target_account_id ON follow_requests(target_account_id);

-- :down

DROP INDEX IF EXISTS idx_follows_account_id;
DROP INDEX IF EXISTS idx_follows_target_account_id;
DROP INDEX IF EXISTS idx_follow_recommendation_mutes_account_id;
DROP INDEX IF EXISTS idx_follow_recommendation_mutes_target_account_id;
DROP INDEX IF EXISTS idx_follow_recommendation_suppressions_mutes_account_id;
DROP INDEX IF EXISTS idx_follow_requests_account_id;
DROP INDEX IF EXISTS idx_follow_requests_target_account_id;

DROP TABLE IF EXISTS follow_requests CASCADE;
DROP TABLE IF EXISTS follow_recommendation_mutes CASCADE;
DROP TABLE IF EXISTS follow_recommendation_suppressions CASCADE;
DROP TABLE IF EXISTS follows CASCADE;
