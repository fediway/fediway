
-- :up
CREATE TABLE IF NOT EXISTS sourcing_runs
(
    id           UUID,
    feed_id      Nullable(UUID),
    rec_run_id   Nullable(UUID),
    rec_step_id  Nullable(UUID),
    group        Nullable(String),
    source       String,
    params       JSON,
    duration_ns  UInt64,
    executed_at  DateTime
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(executed_at)
ORDER BY (executed_at, id);

-- :down
DROP TABLE IF EXISTS sourcing_runs CASCADE;