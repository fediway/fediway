/*
Latest 50 favourited or reblogged status ids for all accounts that have at least 
1 engagement. This can be used to search for statuses similar to the ones that 
an account previously engaged with.
*/

-- :up
CREATE MATERIALIZED VIEW IF NOT EXISTS latest_engaged_statuses AS
SELECT 
	a.id as account_id,
	array_agg(DISTINCT e.status_id) as status_ids
FROM accounts a
INNER JOIN LATERAL (
	SELECT * 
	FROM enriched_status_engagement_events e
	WHERE e.account_id = a.id
	AND e.type IN ('favourite', 'reblog')
	ORDER BY e.event_time DESC
	LIMIT 50
) e
ON e.account_id = a.id
GROUP BY a.id;

CREATE SINK IF NOT EXISTS latest_engaged_statuses_sink
FROM latest_engaged_statuses
WITH (
    connector='kafka',
    properties.bootstrap.server='${bootstrap_server}',
    topic='latest_engaged_statuses',
    primary_key='account_id',
) FORMAT PLAIN ENCODE JSON (
    force_append_only='true'
);

-- :down
DROP VIEW IF EXISTS latest_account_engagements;