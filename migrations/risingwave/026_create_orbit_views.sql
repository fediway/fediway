
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
GROUP BY st.tag_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS orbit_account_tag_engagements AS
SELECT
    e.account_id,
    st.tag_id
FROM enriched_status_engagement_events e
JOIN statuses_tags st ON st.status_id = e.status_id
WHERE e.event_time > NOW() - INTERVAL '90 DAYS'
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

CREATE MATERIALIZED VIEW IF NOT EXISTS orbit_statuses AS
SELECT
    s.id as status_id,
    s.account_id,
    s.created_at,
    ARRAY_REMOVE(t.tags, NULL) as tags
FROM statuses s
LEFT JOIN (
    SELECT status_id, array_agg(tag_id) AS tags 
    FROM statuses_tags t
    GROUP BY status_id
) t ON t.status_id = s.id
WHERE s.created_at > NOW() - INTERVAL '90 DAYS';

CREATE SINK IF NOT EXISTS orbit_statuses_sink
FROM orbit_statuses
WITH (
    connector='kafka',
    properties.bootstrap.server='${bootstrap_server}',
    topic='orbit_statuses',
    primary_key='status_id',
) FORMAT PLAIN ENCODE JSON (
    force_append_only='true'
);

CREATE SINK IF NOT EXISTS orbit_engagements_sink AS 
SELECT
    e.account_id,
    e.status_id,
    e.author_id,
    e.event_time
FROM enriched_status_engagement_events e
WITH (
    connector='kafka',
    properties.bootstrap.server='${bootstrap_server}',
    topic='orbit_engagements',
    primary_key='account_id,status_id',
) FORMAT PLAIN ENCODE JSON (
    force_append_only='true'
);

-- :down

DROP SINK IF EXISTS orbit_statuses_sink;
DROP SINK IF EXISTS orbit_engagements_sink;
DROP VIEW IF EXISTS orbit_account_tag_engagements;
DROP VIEW IF EXISTS orbit_tag_similarities;
DROP VIEW IF EXISTS orbit_tag_performance;