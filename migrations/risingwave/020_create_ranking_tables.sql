
-- :up
CREATE TABLE IF NOT EXISTS ranking_runs (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    rec_run_id VARCHAR,
    rec_step_id VARCHAR,
    ranker VARCHAR,
    params JSONB,
    duration_ns BIGINT,
    executed_at TIMESTAMP
)

CREATE TABLE IF NOT EXISTS ranked_entities (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    ranking_run_id VARCHAR,
    entity VARCHAR,
    entity_id BIGINT,
    features JSONB,
    score REAL,
    meta JSONB,
    created_at TIMESTAMP
)

-- :down
DROP TABLE IF EXISTS ranking_runs CASCADE;
DROP TABLE IF EXISTS ranked_entities CASCADE;