
-- :up

CREATE TABLE IF NOT EXISTS accounts (
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
    also_known_as VARCHAR[],
    silenced_at TIMESTAMP,
    suspended_at TIMESTAMP,
    trendable BOOLEAN,
    indexable BOOLEAN,
    attribution_domains VARCHAR[]
) FROM pg_source TABLE 'public.accounts';

CREATE TABLE IF NOT EXISTS account_conversations (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    conversation_id BIGINT,
    participant_account_ids BIGINT[],
    status_ids BIGINT[],
    last_status_id BIGINT,
    lock_version INT,
    unread BOOLEAN,
) FROM pg_source TABLE 'public.account_conversations';

CREATE TABLE IF NOT EXISTS account_domain_blocks (
    id BIGINT PRIMARY KEY,
    domain VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    account_id BIGINT
) FROM pg_source TABLE 'public.account_domain_blocks';

CREATE TABLE IF NOT EXISTS account_notes (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    target_account_id BIGINT,
    comment TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.account_notes';

CREATE TABLE IF NOT EXISTS account_pins (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    target_account_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.account_pins';

CREATE TABLE IF NOT EXISTS account_stats (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    statuses_count BIGINT,
    following_count BIGINT,
    followers_count BIGINT,
) FROM pg_source TABLE 'public.account_stats';

CREATE INDEX IF NOT EXISTS idx_account_stats_account_id ON account_stats(account_id);

CREATE TABLE IF NOT EXISTS accounts_tags (
    account_id BIGINT,
    tag_id BIGINT,
    PRIMARY KEY (account_id, tag_id)
) FROM pg_source TABLE 'public.accounts_tags';

-- :down

DROP INDEX IF EXISTS idx_account_stats_account_id;

DROP TABLE IF EXISTS accounts_tags CASCADE;
DROP TABLE IF EXISTS account_stats CASCADE;
DROP TABLE IF EXISTS account_pins CASCADE;
DROP TABLE IF EXISTS account_notes CASCADE;
DROP TABLE IF EXISTS account_domain_blocks CASCADE;
DROP TABLE IF EXISTS account_conversations CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;