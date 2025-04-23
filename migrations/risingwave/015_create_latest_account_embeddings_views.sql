
-- :up
CREATE MATERIALIZED VIEW latest_account_favourites_embeddings AS
SELECT a.id AS account_id, (
	SELECT array_agg(embedding ORDER BY favourite_id DESC) AS embeddings
	FROM (
		SELECT ste.embedding AS embedding, f.id AS favourite_id
		FROM favourites f
		JOIN status_text_embeddings ste 
		  ON ste.status_id = f.status_id 
		 AND f.account_id = a.id
		 AND ste.embedding IS NOT NULL
		ORDER BY f.id DESC
		LIMIT ${k_latest_account_favourites_embeddings}
	)
) AS embeddings
FROM accounts a
WHERE EXISTS (
	SELECT f.id 
	FROM favourites f
	JOIN status_text_embeddings ste
	  ON ste.status_id = f.status_id 
	 AND f.account_id = a.id
	 AND ste.embedding IS NOT NULL
);

CREATE MATERIALIZED VIEW latest_account_reblogs_embeddings AS
SELECT a.id AS account_id, (
	SELECT array_agg(embedding ORDER BY reblog_id DESC) as embeddings
	FROM (
		SELECT ste.embedding AS embedding, s.id AS reblog_id
		FROM statuses s
		JOIN status_text_embeddings ste 
		  ON s.reblog_of_id IS NOT NULL
		 AND ste.status_id = s.reblog_of_id
		 AND s.account_id = a.id
		 AND ste.embedding IS NOT NULL
		ORDER BY s.id DESC
		LIMIT ${k_latest_account_reblogs_embeddings}
	)
) AS embeddings
FROM accounts a
WHERE EXISTS (
	SELECT s.id 
	FROM statuses s
	JOIN status_text_embeddings ste 
	  ON s.reblog_of_id IS NOT NULL
	 AND ste.status_id = s.reblog_of_id
	 AND s.account_id = a.id
	 AND ste.embedding IS NOT NULL
);

CREATE MATERIALIZED VIEW latest_account_replies_embeddings AS
SELECT a.id AS account_id, (
	SELECT array_agg(embedding ORDER BY reply_id DESC) AS embeddings
	from (
		SELECT ste.embedding AS embedding, s.id AS reply_id
		FROM statuses s
		JOIN status_text_embeddings ste 
		  ON s.in_reply_to_id IS NOT NULL
		 AND ste.status_id = s.in_reply_to_id
		 AND s.account_id = a.id
		 AND ste.embedding IS NOT NULL
		ORDER BY s.id DESC
		LIMIT ${k_latest_account_replies_embeddings}
	)
) as embeddings
from accounts a
WHERE EXISTS (
	SELECT s.id 
	FROM statuses s
	JOIN status_text_embeddings ste 
	  ON s.in_reply_to_id IS NOT NULL
	 AND ste.status_id = s.in_reply_to_id
	 AND s.account_id = a.id
	 AND ste.embedding IS NOT NULL
);

{% for engagement_type in ['favourites', 'reblogs', 'replies']  %}
	CREATE SINK IF NOT EXISTS latest_account_{{ engagement_type }}_sink
    FROM latest_account_{{ engagement_type }}_embeddings
    WITH (
        connector='kafka',
        properties.bootstrap.server='${bootstrap_server}',
        topic='latest_account_{{ engagement_type }}_embeddings',
        primary_key='account_id',
    ) FORMAT DEBEZIUM ENCODE JSON;
{% endfor -%}

-- :down
DROP VIEW IF EXISTS latest_account_favourites_embeddings;
DROP VIEW IF EXISTS latest_account_reblogs_embeddings;
DROP VIEW IF EXISTS latest_account_replies_embeddings;

{% for engagement_type in ['favourites', 'reblogs', 'replies']  %}
    DROP SINK IF EXISTS latest_account_{{ engagement_type }}_sink;
{% endfor -%}