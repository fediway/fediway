
-- :up
CREATE TABLE IF NOT EXISTS rec_pipeline_runs (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    iteration INT,
    duration_ns BIGINT,
    executed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rec_pipeline_steps (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    run_id VARCHAR,
    group_name VARCHAR,
    name VARCHAR,
    params JSONB,
    duration_ns BIGINT,
    executed_at TIMESTAMP
);

-- :down
DROP TABLE IF EXISTS rec_pipeline_runs CASCADE;
DROP TABLE IF EXISTS rec_pipeline_steps CASCADE;