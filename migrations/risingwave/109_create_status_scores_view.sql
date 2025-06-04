
-- :up

CREATE MATERIALIZED VIEW IF NOT EXISTS account_status_ranks AS
SELECT 
	s.id,
	s.account_id,
	row_number() OVER (PARTITION BY s.account_id ORDER BY s.created_at) r
FROM statuses s
JOIN status_stats st ON st.status_id  = s.id;

CREATE MATERIALIZED VIEW IF NOT EXISTS status_zscores AS
SELECT
	s.id AS status_id,
	s.account_id,
	COUNT(s2.id) AS num_preceding,
	CASE 
		WHEN stddev_samp(s2.favourites_count) > 0
		THEN (max(st.favourites_count) - COALESCE(avg(s2.favourites_count), 0)) / stddev_samp(s2.favourites_count)
		ELSE 0
	END AS favourites_count_zscore,
    CASE 
		WHEN stddev_samp(s2.reblogs_count) > 0
		THEN (max(st.reblogs_count) - COALESCE(avg(s2.reblogs_count), 0)) / stddev_samp(s2.reblogs_count)
		ELSE 0
	END AS reblogs_count_zscore,
    CASE 
		WHEN stddev_samp(s2.replies_count) > 0
		THEN (max(st.replies_count) - COALESCE(avg(s2.replies_count), 0)) / stddev_samp(s2.replies_count)
		ELSE 0
	END AS replies_count_zscore
FROM account_status_ranks s
JOIN (
	SELECT 
		s.*,
		st.favourites_count,
		st.replies_count,
		st.reblogs_count
	FROM account_status_ranks s
	JOIN status_stats st ON st.status_id  = s.id
) s2 ON s.account_id = s2.account_id AND s2.r < s.r AND s2.r >= s.r - 25
JOIN status_stats st ON st.status_id  = s.id
GROUP BY s.id, s.account_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS status_scores AS
SELECT
    s.id AS status_id,
    (
        --- engagements
        (
            st.favourites_count * 0.5 +
            st.reblogs_count * 2.0 +
            st.replies_count * 2.0
        ) / 1.5

        --- zscore multiplier
        * (1 / (1 + exp(
            - least(greatest((
                z.favourites_count_zscore * 0.5 +
                z.reblogs_count_zscore * 2.0 +
                z.replies_count_zscore * 2.0
            ), -20.0), 20.0) / 3
        )))
    ) AS unusual_popularity_score
FROM statuses s
JOIN status_zscores z ON z.status_id = s.id AND z.num_preceding > 10
JOIN status_stats st ON st.status_id = s.id;

-- :down

DROP VIEW IF EXISTS status_scores;
DROP VIEW IF EXISTS status_zscores;