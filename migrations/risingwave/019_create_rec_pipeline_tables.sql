
-- :up
CREATE TABLE IF NOT EXISTS feed_pipeline_runs (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    iteration INT,
    duration_ns BIGINT,
    event_time TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feed_pipeline_steps (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    run_id VARCHAR,
    name VARCHAR,
    params JSONB,
    duration_ns BIGINT,
    event_time TIMESTAMP
);

-- :down
DROP TABLE IF EXISTS rec_pipeline_runs CASCADE;
DROP TABLE IF EXISTS rec_pipeline_steps CASCADE;