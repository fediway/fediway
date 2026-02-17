
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality_score_languages AS
SELECT
    s.status_id,
    s.author_id,
    s.language,
    s.created_at,
    e.weighted_engagement,
    e.unique_domains,
    e.unique_engagers,
    e.first_engagement_at,
    e.last_engagement_at
FROM recent_original_statuses s
JOIN status_engagement_counts e ON e.status_id = s.status_id;

CREATE INDEX IF NOT EXISTS idx_status_virality_language
    ON status_virality_score_languages(language);

-- :down

DROP INDEX IF EXISTS idx_status_virality_language;

DROP MATERIALIZED VIEW IF EXISTS status_virality_score_languages CASCADE;
