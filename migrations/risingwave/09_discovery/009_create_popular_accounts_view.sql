
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS popular_accounts AS
SELECT
    a.id AS author_id,
    a.domain,
    COUNT(f.id) AS follower_count
FROM accounts a
JOIN follows f ON f.target_account_id = a.id
WHERE a.suspended_at IS NULL
  AND a.silenced_at IS NULL
  AND a.created_at < NOW() - INTERVAL '7 DAYS'
GROUP BY a.id, a.domain
HAVING COUNT(f.id) >= 10;

CREATE INDEX IF NOT EXISTS idx_popular_accounts_follower_count
    ON popular_accounts(follower_count DESC);

-- :down

DROP INDEX IF EXISTS idx_popular_accounts_follower_count;

DROP MATERIALIZED VIEW IF EXISTS popular_accounts CASCADE;
