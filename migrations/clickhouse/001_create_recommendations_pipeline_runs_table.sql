
-- :up
CREATE TABLE IF NOT EXISTS rec_pipeline_runs
(
    id           UUID,
    feed_id      Nullable(UUID),
    iteration    UInt16,
    duration_ns  UInt64,
    executed_at  DateTime
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(executed_at)
ORDER BY (executed_at, id);

-- :down
DROP TABLE IF EXISTS rec_pipeline_runs CASCADE;