
-- :up
CREATE TABLE IF NOT EXISTS ranking_runs (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    rec_run_id VARCHAR,
    rec_step_id VARCHAR,
    ranker VARCHAR,
    params JSONB,
    feature_retrival_duration_ns BIGINT,
    ranking_duration_ns BIGINT,
    candidates_count BIGINT,
    executed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ranked_entities (
    id VARCHAR PRIMARY KEY,
    ranking_run_id VARCHAR,
    entity VARCHAR,
    entity_id BIGINT,
    features JSONB,
    score DOUBLE,
    meta JSONB,
    created_at TIMESTAMP
);

-- :down
DROP TABLE IF EXISTS ranking_runs CASCADE;
DROP TABLE IF EXISTS ranked_entities CASCADE;