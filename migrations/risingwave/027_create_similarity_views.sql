
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS account_similarities AS
SELECT 
    e1.account_id as account1,
    e2.account_id as account2,
    COUNT(DISTINCT e1.status_id) as common_items
FROM enriched_status_engagement_events e1
JOIN enriched_status_engagement_events e2 
  ON e1.status_id = e2.status_id 
 AND e2.account_id != e1.author_id -- dont consider engagements between account pair
 AND e2.author_id != e1.account_id
WHERE e1.account_id < e2.account_id 
  AND e1.event_time > NOW() - INTERVAL '90 DAYS'
  AND e2.event_time > NOW() - INTERVAL '90 DAYS'
GROUP BY e1.account_id, e2.account_id
HAVING COUNT(DISTINCT e1.status_id) >= 3; 

CREATE MATERIALIZED VIEW IF NOT EXISTS status_similarities AS
SELECT 
    e1.status_id as status1,
    e2.status_id as status2,
    COUNT(DISTINCT e1.account_id) as common_accounts
FROM enriched_status_engagement_events e1
JOIN enriched_status_engagement_events e2 
  ON e1.account_id = e2.account_id 
 AND e1.author_id != e2.author_id -- dont measure similarity between statuses of the same author
WHERE e1.status_id < e2.status_id
GROUP BY e1.status_id, e2.status_id
HAVING COUNT(DISTINCT e1.account_id) >= 3;

-- :down

DROP VIEW IF EXISTS account_similarities;
DROP VIEW IF EXISTS status_similarities;