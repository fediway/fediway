
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS follows_engaging_candidates AS
SELECT
    fe.user_id,
    fe.status_id,
    fe.author_id,
    fe.engaged_follows_count,
    fe.engaged_follows,
    fe.latest_engagement_time,
    fe.total_engagement_weight,
    s.created_at AS status_created_at,
    s.language
FROM follows_recent_engagements fe
JOIN statuses s ON s.id = fe.status_id
WHERE s.deleted_at IS NULL
  AND s.visibility IN (0, 1)  -- public or unlisted
  AND fe.author_id != fe.user_id;  -- not user's own posts

CREATE INDEX IF NOT EXISTS idx_follows_engaging_candidates_user_id
    ON follows_engaging_candidates(user_id);

CREATE INDEX IF NOT EXISTS idx_follows_engaging_candidates_lookup
    ON follows_engaging_candidates(user_id, engaged_follows_count DESC, latest_engagement_time DESC);

-- :down

DROP INDEX IF EXISTS idx_follows_engaging_candidates_user_id;
DROP INDEX IF EXISTS idx_follows_engaging_candidates_lookup;

DROP MATERIALIZED VIEW IF EXISTS follows_engaging_candidates CASCADE;
