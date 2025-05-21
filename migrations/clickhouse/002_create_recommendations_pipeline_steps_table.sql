
-- :up
CREATE TABLE IF NOT EXISTS recommendations_pipeline_steps
(
    id           UUID,
    feed_id      Nullable(UUID),
    run_id       UUID,
    group        String,
    name         String,
    params       JSON,
    duration_ns  UInt64,
    executed_at  DateTime
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(executed_at)
ORDER BY (executed_at, id);

-- :down
DROP TABLE IF EXISTS recommendations_pipeline_runs CASCADE;