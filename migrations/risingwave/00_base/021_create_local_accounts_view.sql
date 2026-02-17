
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS local_accounts AS
SELECT account_id
FROM users
WHERE confirmed_at IS NOT NULL
  AND disabled = false
  AND approved = true;

CREATE INDEX IF NOT EXISTS idx_local_accounts_account_id
    ON local_accounts(account_id);

-- :down

DROP INDEX IF EXISTS idx_local_accounts_account_id;

DROP MATERIALIZED VIEW IF EXISTS local_accounts CASCADE;
