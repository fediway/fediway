
-- :up

CREATE TABLE IF NOT EXISTS preview_cards (
    id BIGINT PRIMARY KEY,
    url VARCHAR,
    title VARCHAR,
    description VARCHAR,
    type INT,
    author_name VARCHAR,
    author_url VARCHAR,
    provider_name VARCHAR,
    provider_url VARCHAR,
    width INT,
    height INT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    embed_url VARCHAR,
    language VARCHAR,
    max_score DOUBLE,
    max_score_at TIMESTAMP,
    trendable BOOLEAN,
    link_type INT,
    published_at TIMESTAMP,
    author_account_id BIGINT,
) FROM pg_source TABLE 'public.preview_cards';

CREATE INDEX IF NOT EXISTS idx_preview_cards_author_account_id ON preview_cards(author_account_id);

CREATE TABLE IF NOT EXISTS preview_card_providers (
    id BIGINT PRIMARY KEY,
    domain VARCHAR,
    trendable BOOLEAN,
    reviewed_at TIMESTAMP,
    requested_review_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.preview_card_providers';

CREATE TABLE IF NOT EXISTS preview_cards_statuses (
    preview_card_id BIGINT,
    status_id BIGINT,
    PRIMARY KEY (preview_card_id, status_id)
) FROM pg_source TABLE 'public.preview_cards_statuses';

-- :down

DROP INDEX IF EXISTS idx_preview_cards_author_account_id;

DROP TABLE IF EXISTS preview_cards_statuses CASCADE;
DROP TABLE IF EXISTS preview_card_providers CASCADE;
DROP TABLE IF EXISTS preview_cards CASCADE;
