
-- :up
CREATE MATERIALIZED VIEW IF NOT EXISTS enriched_account_stats AS
SELECT 
	a.account_id, 
	a.statuses_count,
    a.following_count,
    a.followers_count,
	SUM(ss.favourites_count)::INT as favourites_count_90d,
	SUM(ss.reblogs_count)::INT as reblogs_count_90d,
	SUM(ss.replies_count)::INT as replies_count_90d,
	AVG(ss.favourites_count)::INT as avg_favourites_90d,
	AVG(ss.reblogs_count)::INT as avg_reblogs_90d,
	AVG(ss.replies_count)::INT as avg_replies_90d,
	MAX(ss.favourites_count)::INT as max_favourites_90d,
	MAX(ss.reblogs_count)::INT as max_reblogs_90d,
	MAX(ss.replies_count)::INT as max_replies_90d
FROM account_stats a
JOIN statuses s ON s.account_id = a.account_id AND s.created_at >= NOW() - INTERVAL '90 days'
JOIN status_stats ss ON ss.status_id = s.id
GROUP BY 
	a.account_id, 
	a.statuses_count,
    a.following_count,
    a.followers_count;

CREATE SINK IF NOT EXISTS enriched_account_stats_sink
FROM enriched_account_stats
WITH (
    connector='kafka',
    properties.bootstrap.server='${bootstrap_server}',
    topic='enriched_account_stats',
    primary_key='account_id',
) FORMAT DEBEZIUM ENCODE JSON;

-- :down
DROP VIEW IF EXISTS enriched_account_stats;
DROP SINK IF EXISTS enriched_account_stats_sink;
