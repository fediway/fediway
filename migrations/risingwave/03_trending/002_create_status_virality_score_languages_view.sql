
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS status_virality_score_languages AS
SELECT
    s.id AS status_id,
    s.account_id AS author_id,
    s.language,
    s.created_at,
    COALESCE(e.num_favs, 0) AS num_favs,
    COALESCE(e.num_reblogs, 0) AS num_reblogs,
    COALESCE(e.num_replies, 0) AS num_replies,
    COALESCE(e.unique_engagers, 0) AS unique_engagers,
    COALESCE(e.unique_domains, 1) AS unique_domains,
    COALESCE(e.weighted_engagement, 0) AS engagement,
    GREATEST(
        EXTRACT(EPOCH FROM (NOW() - s.created_at)) / 3600,
        0.1
    ) AS age_hours,
    COALESCE(e.weighted_engagement, 0) / GREATEST(
        EXTRACT(EPOCH FROM (NOW() - s.created_at)) / 3600,
        0.1
    ) AS velocity,
    -- Base score (HN-style with gravity 1.5)
    LN(1 + COALESCE(e.weighted_engagement, 0)) /
        POWER(
            GREATEST(EXTRACT(EPOCH FROM (NOW() - s.created_at)) / 3600, 0.1) + 2,
            1.5
        ) AS base_score,
    -- Domain bonus: modest multiplier for cross-instance engagement
    (1 + 0.1 * LN(1 + COALESCE(e.unique_domains, 1))) AS domain_bonus,
    -- Final score = base_score * domain_bonus
    (
        LN(1 + COALESCE(e.weighted_engagement, 0)) /
        POWER(
            GREATEST(EXTRACT(EPOCH FROM (NOW() - s.created_at)) / 3600, 0.1) + 2,
            1.5
        )
    ) * (1 + 0.1 * LN(1 + COALESCE(e.unique_domains, 1))) AS score
FROM statuses s
LEFT JOIN status_engagement_counts e ON e.status_id = s.id
WHERE s.created_at > NOW() - INTERVAL '24 HOURS'
  AND s.visibility = 0
  AND s.reblog_of_id IS NULL
  AND s.in_reply_to_id IS NULL
  AND s.deleted_at IS NULL
  AND COALESCE(e.unique_engagers, 0) >= 3;

CREATE INDEX IF NOT EXISTS idx_status_virality_language
    ON status_virality_score_languages(language);

CREATE INDEX IF NOT EXISTS idx_status_virality_score
    ON status_virality_score_languages(score DESC);

CREATE INDEX IF NOT EXISTS idx_status_virality_language_score
    ON status_virality_score_languages(language, score DESC);

-- :down

DROP INDEX IF EXISTS idx_status_virality_language_score;
DROP INDEX IF EXISTS idx_status_virality_score;
DROP INDEX IF EXISTS idx_status_virality_language;

DROP MATERIALIZED VIEW IF EXISTS status_virality_score_languages CASCADE;
