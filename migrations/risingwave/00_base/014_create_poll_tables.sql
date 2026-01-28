
-- :up

CREATE TABLE IF NOT EXISTS polls (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    status_id BIGINT,
    expires_at TIMESTAMP,
    options VARCHAR[],
    cached_tallies BIGINT[],
    multiple BOOLEAN,
    hide_totals BOOLEAN,
    last_fetched_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    lock_version INT,
    voters_count BIGINT,
) FROM pg_source TABLE 'public.polls';

CREATE INDEX IF NOT EXISTS idx_polls_account_id ON polls(account_id);
CREATE INDEX IF NOT EXISTS idx_polls_status_id ON polls(status_id);

CREATE TABLE IF NOT EXISTS poll_votes (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    poll_id BIGINT,
    choice INT,
    uri VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.poll_votes';

CREATE INDEX IF NOT EXISTS idx_poll_votes_account_id ON poll_votes(account_id);
CREATE INDEX IF NOT EXISTS idx_poll_votes_poll_id ON poll_votes(poll_id);

-- :down

DROP INDEX IF EXISTS idx_polls_account_id;
DROP INDEX IF EXISTS idx_polls_status_id;
DROP INDEX IF EXISTS idx_poll_votes_account_id;
DROP INDEX IF EXISTS idx_poll_votes_poll_id;

DROP TABLE IF EXISTS poll_votes CASCADE;
DROP TABLE IF EXISTS polls CASCADE;
