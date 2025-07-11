
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS orbit_tag_performance AS
SELECT
    st.tag_id,
    COUNT(DISTINCT e.account_id) AS num_engaged_accounts,
    COUNT(DISTINCT e.author_id) AS num_authors,
    COUNT(DISTINCT e.status_id) AS num_statuses
FROM enriched_status_engagement_events e
JOIN statuses_tags st ON st.status_id = e.status_id
WHERE e.event_time > NOW() - INTERVAL '90 DAYS'
  AND e.author_silenced_at IS NULL 
  AND e.account_silenced_at IS NULL
  AND e.sensitive != true
GROUP BY st.tag_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS orbit_account_tag_engagements AS
SELECT
    e.account_id,
    st.tag_id
FROM enriched_status_engagement_events e
JOIN statuses_tags st ON st.status_id = e.status_id
WHERE e.event_time > NOW() - INTERVAL '90 DAYS'
  AND e.author_silenced_at IS NULL 
  AND e.account_silenced_at IS NULL
  AND e.sensitive != true
GROUP BY e.account_id, st.tag_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS orbit_tag_similarities AS
SELECT
    e1.tag_id AS tag1,
    e2.tag_id AS tag2,
    (
        COUNT(distinct e1.account_id) / 
        SQRT(MAX(t1.num_engaged_accounts) * MAX(t2.num_engaged_accounts))
    ) as cosine_sim
FROM orbit_account_tag_engagements e1
JOIN orbit_account_tag_engagements e2 ON e2.account_id = e1.account_id
JOIN orbit_tag_performance t1 ON t1.tag_id = e1.tag_id AND t1.num_engaged_accounts >= 15
JOIN orbit_tag_performance t2 ON t2.tag_id = e2.tag_id AND t2.num_engaged_accounts >= 15
WHERE e1.tag_id < e2.tag_id
GROUP BY e1.tag_id, e2.tag_id;

-- :down

DROP VIEW IF EXISTS orbit_account_tag_engagements;
DROP VIEW IF EXISTS orbit_tag_similarities;
DROP VIEW IF EXISTS orbit_tag_performance;