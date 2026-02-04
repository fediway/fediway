
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS user_author_affinity AS
SELECT
    account_id AS user_id,
    author_id,
    COUNT(*) FILTER (WHERE type = 0) AS num_favs,
    COUNT(*) FILTER (WHERE type = 1) AS num_reblogs,
    COUNT(*) FILTER (WHERE type = 2) AS num_replies,
    COUNT(*) FILTER (WHERE type = 4) AS num_bookmarks,
    COUNT(*) FILTER (WHERE type = 5) AS num_quotes,
    (
        COUNT(*) FILTER (WHERE type = 0) * 1.0 +
        COUNT(*) FILTER (WHERE type = 1) * 2.0 +
        COUNT(*) FILTER (WHERE type = 2) * 3.0 +
        COUNT(*) FILTER (WHERE type = 4) * 0.5 +
        COUNT(*) FILTER (WHERE type = 5) * 2.0
    ) AS raw_affinity
FROM enriched_status_engagement_events
WHERE event_time > NOW() - INTERVAL '60 DAYS'
GROUP BY account_id, author_id;

CREATE INDEX IF NOT EXISTS idx_user_author_affinity_user_id
    ON user_author_affinity(user_id);

CREATE INDEX IF NOT EXISTS idx_user_author_affinity_author_id
    ON user_author_affinity(author_id);

CREATE INDEX IF NOT EXISTS idx_user_author_affinity_lookup
    ON user_author_affinity(user_id, author_id);

-- :down

DROP INDEX IF EXISTS idx_user_author_affinity_lookup;
DROP INDEX IF EXISTS idx_user_author_affinity_author_id;
DROP INDEX IF EXISTS idx_user_author_affinity_user_id;

DROP MATERIALIZED VIEW IF EXISTS user_author_affinity CASCADE;
