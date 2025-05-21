
-- :up
CREATE TABLE IF NOT EXISTS feeds
(
    id           UUID,
    user_agent   Nullable(String),
    ip           Nullable(String),
    name         String,
    entity       JSON,
    account_id   Nullable(String),
    executed_at  DateTime
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(executed_at)
ORDER BY (executed_at, id);

-- :down
DROP TABLE IF EXISTS feeds CASCADE;