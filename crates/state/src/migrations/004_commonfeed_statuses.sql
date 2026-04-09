CREATE SEQUENCE commonfeed_statuses_id_seq;

CREATE TABLE commonfeed_statuses (
    id                  BIGINT PRIMARY KEY DEFAULT timestamp_id('commonfeed_statuses'),
    provider_domain     TEXT NOT NULL,
    remote_id           BIGINT NOT NULL,
    post_url            TEXT NOT NULL,
    post_uri            TEXT NOT NULL DEFAULT '',
    post_data           JSONB NOT NULL,
    cached_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider_domain, remote_id)
);

CREATE INDEX idx_commonfeed_statuses_cached
    ON commonfeed_statuses (cached_at);
