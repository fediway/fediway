
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS account_status_labels AS
SELECT
    se.status_id,
    se.account_id,
    MIN(se.author_id) as author_id,
    MIN(s.created_at) AS status_created_at,
    BOOL_OR(se.type = 'favourite') as is_favourited,
    MIN(CASE WHEN se.type = 'favourite' THEN se.event_time END) AS is_favourited_at,
    BOOL_OR(se.type = 'reblog') as is_reblogged,
    MIN(CASE WHEN se.type = 'reblog' THEN se.event_time END) AS is_reblogged_at,
    BOOL_OR(se.type = 'reply') as is_replied,
    MIN(CASE WHEN se.type = 'reply' THEN se.event_time END) AS is_replied_at,
    BOOL_OR(author_se.status_id IS NOT NULL) as is_reply_engaged_by_author,
    MIN(author_se.event_time) AS is_reply_engaged_by_author_at
FROM enriched_status_engagement_events se
LEFT JOIN status_engagement_events author_se 
    ON author_se.account_id = se.author_id
    AND author_se.status_id = se.reply_id
    AND se.reply_id IS NOT NULL
JOIN statuses s ON s.id = se.status_id
GROUP BY se.account_id, se.status_id;

-- :down

DROP VIEW IF EXISTS account_status_labels;