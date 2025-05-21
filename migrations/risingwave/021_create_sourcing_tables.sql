
-- :up
CREATE TABLE IF NOT EXISTS sourcing_runs (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    step_id VARCHAR,
    group_name VARCHAR,
    source VARCHAR,
    candidates_limit INT,
    candidates_count INT,
    params JSONB,
    duration_ns BIGINT,
    executed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recommendation_sources (
    recommendation_id VARCHAR,
    sourcing_run_id VARCHAR,
    PRIMARY KEY (recommendation_id, sourcing_run_id)
);

-- :down
DROP TABLE IF EXISTS sourcing_runs CASCADE;
DROP TABLE IF EXISTS recommendation_sources CASCADE;