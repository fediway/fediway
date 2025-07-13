
-- :up

{% for window_size, spec in [('24 HOURS', '1d'), ('7 DAYS', '7d'), ('60 DAYS', '60d')] %}
  CREATE MATERIALIZED VIEW IF NOT EXISTS online_features_account_preview_card_domain_engagement_{{ spec }} AS
  SELECT
      e.account_id,
      d.domain as preview_card_domain,
      MAX(event_time)::TIMESTAMP as event_time,
      COUNT(*) AS num_all,
      APPROX_COUNT_DISTINCT(author_id) as num_authors,
      APPROX_COUNT_DISTINCT(e.status_id) as num_statuses,
      APPROX_COUNT_DISTINCT(target_domain) as num_target_domains,
      COUNT(*) FILTER (WHERE type = 0) AS num_favs,
      COUNT(*) FILTER (WHERE type = 1) AS num_reblogs,
      COUNT(*) FILTER (WHERE type = 2) AS num_replies,
      COUNT(*) FILTER (WHERE type = 3) AS num_poll_votes,
      COUNT(*) FILTER (WHERE type = 4) AS num_bookmarks,
      COUNT(*) FILTER (WHERE type = 5) AS num_quotes,
      COUNT(*) FILTER (WHERE has_link) as num_has_link,
      COUNT(*) FILTER (WHERE has_photo_link) as num_has_photo_link,
      COUNT(*) FILTER (WHERE has_video_link) as num_has_video_link,
      COUNT(*) FILTER (WHERE has_rich_link) as num_has_rich_link,
      COUNT(*) FILTER (WHERE has_poll) as num_has_poll,
      COUNT(*) FILTER (WHERE has_image) as num_has_image,
      COUNT(*) FILTER (WHERE has_gifv) as num_has_gifv,
      COUNT(*) FILTER (WHERE has_video) as num_has_video,
      COUNT(*) FILTER (WHERE has_audio) as num_has_audio,
      COUNT(*) FILTER (WHERE has_quote) as num_has_quote,
      AVG(fav_count) AS avg_status_fav_count,
      MAX(fav_count) AS max_status_fav_count,
      MIN(fav_count) AS min_status_fav_count,
      AVG(reblogs_count) AS avg_status_reblogs_count,
      MAX(reblogs_count) AS max_status_reblogs_count,
      MIN(reblogs_count) AS min_status_reblogs_count,
      AVG(replies_count) AS avg_status_replies_count,
      MAX(replies_count) AS max_status_replies_count,
      MIN(replies_count) AS min_status_replies_count,
      AVG(num_mentions) AS avg_mentions,
      AVG(num_tags) AS avg_tags
  FROM enriched_status_engagement_events e
  JOIN preview_cards_statuses p ON e.status_id = p.status_id
  JOIN preview_card_domains d ON d.preview_card_id = p.preview_card_id
  WHERE event_time >= NOW() - INTERVAL '{{ window_size }}'
  -- compute features only for users on our instance
  AND EXISTS (SELECT 1 FROM users u WHERE u.account_id = e.account_id) 
  GROUP BY e.account_id, d.domain;
  
  CREATE SINK IF NOT EXISTS online_features_account_preview_card_domain_engagement_{{ spec }}_sink
  FROM online_features_account_preview_card_domain_engagement_{{ spec }}
  WITH (
    connector='kafka',
    properties.bootstrap.server='{{ bootstrap_server }}',
    topic='online_features_account_preview_card_domain_engagement_{{ spec }}',
    primary_key='account_id,preview_card_domain',
    properties.linger.ms='10000',
  ) FORMAT PLAIN ENCODE JSON (
    force_append_only='true'
  );

  CREATE TABLE IF NOT EXISTS offline_features_account_preview_card_domain_engagement_{{ spec }} (
    account_id BIGINT,
    preview_card_domain BIGINT,
    event_time TIMESTAMP,
    num_all INT,
    num_authors INT,
    num_statuses INT,
    num_target_domains INT,
    num_favs INT,
    num_reblogs INT,
    num_replies INT,
    num_poll_votes INT,
    num_bookmarks INT,
    num_links INT,
    num_photo_links INT,
    num_video_links INT,
    num_rich_links INT,
    num_polls INT,
    num_images INT,
    num_gifvs INT,
    num_videos INT,
    num_audios INT,
    avg_status_fav_count FLOAT,
    max_status_fav_count INT,
    min_status_fav_count INT,
    avg_status_reblogs_count FLOAT,
    max_status_reblogs_count INT,
    min_status_reblogs_count INT,
    avg_status_replies_count FLOAT,
    max_status_replies_count INT,
    min_status_replies_count INT,
    avg_mentions FLOAT,
    avg_tags FLOAT,
    PRIMARY KEY (account_id, preview_card_domain, event_time)
  ) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='offline_features_account_preview_card_domain_engagement_{{ spec }}',
    properties.bootstrap.server='{{ bootstrap_server }}',
  ) FORMAT PLAIN ENCODE JSON;
{% endfor %}

-- :down

{% for spec in ['1d', '7d', '56d'] %}
    DROP SINK IF EXISTS online_features_account_preview_card_domain_engagement_{{ spec }}_sink;
    DROP VIEW IF EXISTS online_features_account_preview_card_domain_engagement_{{ spec }};
    DROP TABLE IF EXISTS offline_features_account_preview_card_domain_engagement_{{ spec }};
{% endfor %}