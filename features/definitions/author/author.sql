-- :up
CREATE MATERIALIZED VIEW IF NOT EXISTS author_engagements AS
SELECT 
    window_start, 
    window_end, 
    account_id, 
    author_id, 
FROM status_engagements
GROUP BY author_id, window_start, window_end;

CREATE MATERIALIZED VIEW IF NOT EXISTS account_author_features AS
-- WITH PRIMARY KEY (account_id, author_id, window_end) AS
SELECT
    account_id, 
    author_id, 
    window_end, 

    -- 7d
    SUM(fav_count) OVER (PARTITION BY account_id, author_id ORDER BY window_end ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS fav_count_7d,
    SUM(reblogs_count) OVER (PARTITION BY account_id, author_id ORDER BY window_end ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS reblogs_count_7d,
    SUM(replies_count) OVER (PARTITION BY account_id, author_id ORDER BY window_end ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS replies_count_7d,

    -- 30d
    SUM(fav_count) OVER (PARTITION BY account_id, author_id ORDER BY window_end ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS fav_count_30d,
    SUM(reblogs_count) OVER (PARTITION BY account_id, author_id ORDER BY window_end ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS reblogs_count_30d,
    SUM(replies_count) OVER (PARTITION BY account_id, author_id ORDER BY window_end ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS replies_count_30d
FROM account_author_features_daily;

CREATE SINK account_author_features_sink
FROM account_author_features
WITH (
    connector='kafka',
    properties.bootstrap.server='${bootstrap_server}',
    topic='account_author_features',
    primary_key='account_id,author_id,window_end',
) FORMAT DEBEZIUM ENCODE JSON;

-- :down
DROP SINK IF EXISTS account_author_features_sink;
DROP VIEW IF EXISTS account_author_features_daily;
DROP VIEW IF EXISTS author_engagements;
