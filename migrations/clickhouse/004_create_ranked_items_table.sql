
-- :up
CREATE TABLE IF NOT EXISTS ranked_items
(
    id             UUID,
    feed_id        Nullable(UUID),
    ranking_run_id Nullable(UUID),
    item_type      String,
    item_id        UInt64
    features       JSON
    score          Float32
    meta           JSON
    created_at     DateTime
)
ENGINE = MergeTree()
PARTITION BY (item_type, toYYYYMM(created_at))
ORDER BY (item_type, created_at);

-- :down
DROP TABLE IF EXISTS ranked_items CASCADE;