ALTER TABLE commonfeed_statuses
    ADD COLUMN mastodon_local_id BIGINT;

CREATE INDEX idx_commonfeed_statuses_mastodon_local
    ON commonfeed_statuses (mastodon_local_id)
    WHERE mastodon_local_id IS NOT NULL;
