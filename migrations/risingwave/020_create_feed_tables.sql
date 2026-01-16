
-- :up

CREATE TABLE IF NOT EXISTS feeds (
    id VARCHAR PRIMARY KEY,
    user_agent VARCHAR,
    ip VARCHAR,
    name VARCHAR,
    entity VARCHAR,
    account_id BIGINT,
    event_time TIMESTAMP,
) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='feeds',
    properties.bootstrap.server='{{ bootstrap_server }}',
) FORMAT PLAIN ENCODE JSON;

CREATE TABLE IF NOT EXISTS feed_pipeline_runs (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    iteration INT,
    duration_ns BIGINT,
    event_time TIMESTAMP
) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='feed_pipeline_runs',
    properties.bootstrap.server='{{ bootstrap_server }}',
) FORMAT PLAIN ENCODE JSON;

CREATE TABLE IF NOT EXISTS feed_pipeline_steps (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    pipeline_run_id VARCHAR,
    name VARCHAR,
    params JSONB,
    duration_ns BIGINT,
    event_time TIMESTAMP
) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='feed_pipeline_steps',
    properties.bootstrap.server='{{ bootstrap_server }}',
) FORMAT PLAIN ENCODE JSON;

CREATE TABLE IF NOT EXISTS feed_sourcing_runs (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    pipeline_step_id VARCHAR,
    source VARCHAR,
    candidates_limit INT,
    candidates_count INT,
    params JSONB,
    duration_ns BIGINT,
    event_time TIMESTAMP
) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='feed_sourcing_runs',
    properties.bootstrap.server='{{ bootstrap_server }}',
) FORMAT PLAIN ENCODE JSON;

CREATE TABLE IF NOT EXISTS feed_recommendations (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    pipeline_run_id VARCHAR,
    entity VARCHAR,
    entity_id BIGINT,
    sources VARCHAR[],
    groups VARCHAR[],
    score REAL,
    event_time TIMESTAMP
) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='feed_recommendations',
    properties.bootstrap.server='{{ bootstrap_server }}',
) FORMAT PLAIN ENCODE JSON;

CREATE TABLE IF NOT EXISTS feed_candidate_sources (
    entity_id VARCHAR,
    entity BIGINT,
    sourcing_run_id VARCHAR,
    PRIMARY KEY (entity_id, entity, sourcing_run_id)
) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='feed_candidate_sources',
    properties.bootstrap.server='{{ bootstrap_server }}',
) FORMAT PLAIN ENCODE JSON;

CREATE TABLE IF NOT EXISTS feed_ranking_runs (
    id VARCHAR PRIMARY KEY,
    feed_id VARCHAR,
    pipeline_run_id VARCHAR,
    pipeline_step_id VARCHAR,
    ranker VARCHAR,
    params JSONB,
    feature_retrival_duration_ns BIGINT,
    ranking_duration_ns BIGINT,
    candidates_count BIGINT,
    event_time TIMESTAMP
) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='feed_ranking_runs',
    properties.bootstrap.server='{{ bootstrap_server }}',
) FORMAT PLAIN ENCODE JSON;

-- :down

DROP TABLE IF EXISTS feeds CASCADE;
DROP TABLE IF EXISTS feed_pipeline_runs CASCADE;
DROP TABLE IF EXISTS feed_pipeline_steps CASCADE;
DROP TABLE IF EXISTS feed_candidate_sources CASCADE;
DROP TABLE IF EXISTS feed_ranking_runs CASCADE;
DROP TABLE IF EXISTS feed_recommendations CASCADE;
DROP TABLE IF EXISTS feed_recommendation_sources CASCADE;
DROP TABLE IF EXISTS feed_ranking_runs CASCADE;