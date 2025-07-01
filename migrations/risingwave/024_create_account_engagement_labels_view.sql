
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS account_engagement_labels AS
SELECT
    e.account_id,
    e.status_id,
    e.event_time,

    -- is_favourited
    e.type = 0 as is_favourited,
    CASE WHEN e.type = 0 THEN e.event_time END AS is_favourited_at,

    -- is_reblogged
    e.type = 1 as is_reblogged,
    CASE WHEN e.type = 1 THEN e.event_time END AS is_reblogged_at,

    -- is_replied
    e.type = 2 as is_replied,
    CASE WHEN e.type = 2 THEN e.event_time END AS is_replied_at,

    -- is_poll_voted
    e.type = 3 as is_poll_voted,
    CASE WHEN e.type = 3 THEN e.event_time END AS is_poll_voted_at,

    -- is_bookmarked
    e.type = 4 as is_bookmarked,
    CASE WHEN e.type = 4 THEN e.event_time END AS is_bookmarked_at,

    -- is_reply_engaged_by_author
    author_e.status_id IS NOT NULL as is_reply_engaged_by_author,
    author_e.event_time AS is_reply_engaged_by_author_at

FROM enriched_status_engagement_events e

-- for is_reply_engaged_by_author label
LEFT JOIN (
    SELECT account_id, status_id, MIN(event_time) AS event_time
    FROM enriched_status_engagement_events
    GROUP BY account_id, status_id
) author_e
 ON author_e.account_id = e.author_id
AND author_e.status_id = e.reply_id

-- create labels only for users on our instance
WHERE EXISTS (SELECT 1 FROM users u WHERE u.account_id = e.account_id);

-- :down

DROP VIEW IF EXISTS account_engagement_labels;