
-- :up
CREATE MATERIALIZED VIEW latest_account_favourites_embeddings AS
SELECT a.id as account_id, (
	select array_agg(embedding order by favourite_id desc) as embeddings
	from (
		select ste.embedding as embedding, f.id as favourite_id
		from favourites f
		join status_text_embeddings ste 
		  on ste.status_id = f.status_id 
		  and f.account_id = a.id
		  and ste.embedding is not null
		order by f.id desc
		limit ${k_latest_account_favourites_embeddings}
	)
) as embeddings
from accounts a;

CREATE MATERIALIZED VIEW latest_account_reblogs_embeddings AS
SELECT a.id as account_id, (
	select array_agg(embedding order by reblog_id desc) as embeddings
	from (
		select ste.embedding as embedding, s.id as reblog_id
		from statuses s
		join status_text_embeddings ste 
		  on s.reblog_of_id is not null
		 and ste.status_id = s.reblog_of_id
		 and s.account_id = a.id
		 and ste.embedding is not null
		order by s.id desc
		limit ${k_latest_account_reblogs_embeddings}
	)
) as embeddings
from accounts a;

CREATE MATERIALIZED VIEW latest_account_replies_embeddings AS
SELECT a.id as account_id, (
	select array_agg(embedding order by reply_id desc) as embeddings
	from (
		select ste.embedding as embedding, s.id as reply_id
		from statuses s
		join status_text_embeddings ste 
		  on s.in_reply_to_id is not null
		 and ste.status_id = s.in_reply_to_id
		 and s.account_id = a.id
		 and ste.embedding is not null
		order by s.id desc
		limit ${k_latest_account_replies_embeddings}
	)
) as embeddings
from accounts a;

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