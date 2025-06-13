
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS account_sim_recommendations AS
SELECT 
	*,
	rank() OVER (
		PARTITION BY account_id	
		ORDER BY score DESC
	) AS rank
FROM (
	SELECT 
	    a.id AS account_id,
	    e.status_id,
	    (COUNT(DISTINCT sim.account2) * LOG(SUM(sim.common_items))) AS score
	FROM accounts a
	JOIN account_similarities sim ON sim.account1 = a.id
	JOIN enriched_status_engagement_events e ON sim.account2 = e.account_id
	JOIN statuses s ON s.id = e.status_id AND s.account_id != a.id AND s.created_at > NOW() - interval '3 DAYS'
	WHERE NOT EXISTS (
		SELECT * FROM enriched_status_engagement_events e_self WHERE e_self.status_id = e.status_id AND e_self.account_id = a.id
	)
	GROUP BY a.id, e.status_id
	HAVING COUNT(DISTINCT sim.account2) > 1
	UNION ALL
	SELECT 
	    a.id AS account_id,
	    e.status_id,
	    (COUNT(DISTINCT sim.account1) * LOG(SUM(sim.common_items))) AS score
	FROM accounts a
	JOIN account_similarities sim ON sim.account2 = a.id
	JOIN enriched_status_engagement_events e ON sim.account1 = e.account_id
	JOIN statuses s ON s.id = e.status_id AND s.account_id != a.id AND s.created_at > NOW() - interval '3 DAYS'
	WHERE NOT EXISTS (
		SELECT * FROM enriched_status_engagement_events e_self WHERE e_self.status_id = e.status_id AND e_self.account_id = a.id
	)
	GROUP BY a.id, e.status_id
	HAVING COUNT(DISTINCT sim.account1) > 1
);

CREATE MATERIALIZED VIEW IF NOT EXISTS status_sim_recommendations AS
SELECT 
	*,
	rank() OVER (
		PARTITION BY account_id	
		ORDER BY score DESC
	) AS rank
FROM (
	SELECT 
		a.id AS account_id,
		sim.status2 as status_id,
		COUNT(distinct e.status_id) * LOG(SUM(sim.common_accounts)) as score
	FROM accounts a
	JOIN enriched_status_engagement_events e ON a.id = e.account_id
	JOIN status_similarities sim ON sim.status1 = e.status_id
	JOIN statuses s ON s.id = e.status_id AND s.account_id != a.id AND s.created_at > NOW() - interval '7 DAYS'
	WHERE NOT EXISTS (
		SELECT * FROM enriched_status_engagement_events e_self WHERE e_self.status_id = sim.status2 AND e_self.account_id = a.id
	)
	GROUP BY a.id, sim.status2
	UNION ALL
		SELECT 
		a.id AS account_id,
		sim.status1 as status_id,
		COUNT(distinct e.status_id) * LOG(SUM(sim.common_accounts)) as score
	FROM accounts a
	JOIN enriched_status_engagement_events e ON a.id = e.account_id
	JOIN status_similarities sim ON sim.status2 = e.status_id
	JOIN statuses s ON s.id = e.status_id AND s.account_id != a.id AND s.created_at > NOW() - interval '7 DAYS'
	WHERE NOT EXISTS (
		SELECT * FROM enriched_status_engagement_events e_self WHERE e_self.status_id = sim.status1 AND e_self.account_id = a.id
	)
	GROUP BY a.id, sim.status1
);

CREATE SINK IF NOT EXISTS account_sim_recommendations_sink AS
SELECT 
	r.account_id, 
	array_agg(r.status_id) as status_ids,
	array_agg(r.score) as scores
FROM account_sim_recommendations r
WHERE r.rank <= 100
GROUP BY account_id
WITH (
    primary_key = 'account_id',
    connector = 'redis',
    redis.url= '{{ redis_url }}',
) FORMAT PLAIN ENCODE TEMPLATE (
    force_append_only='true',
    key_format = 'rec:account_sim:{account_id}',
    value_format = 'status_ids:{status_ids},scores:{scores}'
);

CREATE SINK IF NOT EXISTS status_sim_recommendations_sink AS
SELECT 
	r.account_id, 
	array_agg(r.status_id) as status_ids,
	array_agg(r.score) as scores
FROM status_sim_recommendations r
WHERE r.rank <= 100
GROUP BY account_id
WITH (
    primary_key = 'account_id',
    connector = 'redis',
    redis.url= '{{ redis_url }}',
) FORMAT PLAIN ENCODE TEMPLATE (
    force_append_only='true',
    key_format = 'rec:account_sim:{account_id}',
    value_format = 'status_ids:{status_ids},scores:{scores}'
);

-- :down

DROP SINK IF EXISTS account_sim_recommendations_sink;
DROP SINK IF EXISTS status_sim_recommendations_sink;
DROP VIEW IF EXISTS account_sim_recommendations CASCADE;
DROP VIEW IF EXISTS status_sim_recommendations CASCADE;