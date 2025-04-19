-- :up
CREATE MATERIALIZED VIEW IF NOT EXISTS author_engagement_all_hourly AS
SELECT
  window_start, 
  window_end,
  author_id,
  COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count,
  COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count,
  COUNT(*) FILTER (WHERE type = 'reply') AS replies_count,
  SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images,
  SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs,
  SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos,
  SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios,
  SUM(num_mentions) AS num_mentions
FROM 
  TUMBLE (enriched_status_engagements, event_time, INTERVAL '1 HOUR')
GROUP BY author_id, window_start, window_end;

CREATE MATERIALIZED VIEW IF NOT EXISTS author_engagement_all_features AS
SELECT
    author_id, 
    window_end as event_time, 

    -- 1d
    SUM(num_images) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS num_images_1d,
    SUM(num_gifvs) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS num_gifvs_1d,
    SUM(num_videos) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS num_videos_1d,
    SUM(num_audios) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS num_audios_1d,
    SUM(fav_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS fav_count_1d,
    SUM(reblogs_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS reblogs_count_1d,
    SUM(replies_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS replies_count_1d,

    -- 7d
    SUM(num_images) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS num_images_7d,
    SUM(num_gifvs) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS num_gifvs_7d,
    SUM(num_videos) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS num_videos_7d,
    SUM(num_audios) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS num_audios_7d,
    SUM(fav_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS fav_count_7d,
    SUM(reblogs_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS reblogs_count_7d,
    SUM(replies_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS replies_count_7d,

    -- 30d
    SUM(num_images) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS num_images_30d,
    SUM(num_gifvs) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS num_gifvs_30d,
    SUM(num_videos) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS num_videos_30d,
    SUM(num_audios) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS num_audios_30d,
    SUM(fav_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS fav_count_30d,
    SUM(reblogs_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS reblogs_count_30d,
    SUM(replies_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS replies_count_30d
FROM author_engagement_all_hourly;

CREATE SINK IF NOT EXISTS author_engagement_all_features_sink
FROM author_engagement_all_features
WITH (
    connector='kafka',
    properties.bootstrap.server='${bootstrap_server}',
    topic='author_engagement_all_features',
    primary_key='author_id,event_time',
) FORMAT DEBEZIUM ENCODE JSON;

{% for type in ['favourite', 'reblog', 'reply'] -%}
  CREATE MATERIALIZED VIEW IF NOT EXISTS author_engagement_is_{{ type }}_hourly AS
  SELECT
    window_start, 
    window_end,
    author_id,
    SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as num_images,
    SUM(CASE WHEN has_gifv THEN 1 ELSE 0 END) as num_gifvs,
    SUM(CASE WHEN has_video THEN 1 ELSE 0 END) as num_videos,
    SUM(CASE WHEN has_audio THEN 1 ELSE 0 END) as num_audios,
    SUM(num_mentions) AS num_mentions
  FROM 
    TUMBLE (enriched_status_engagements, event_time, INTERVAL '1 HOUR')
  WHERE
    type = '{{ type }}'
  GROUP BY author_id, window_start, window_end;

  CREATE MATERIALIZED VIEW IF NOT EXISTS author_engagement_is_{{ type }}_features AS
  SELECT
      author_id, 
      window_end as event_time, 

      -- 1d
      SUM(num_images) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS num_images_1d,
      SUM(num_gifvs) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS num_gifvs_1d,
      SUM(num_videos) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS num_videos_1d,
      SUM(num_audios) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS num_audios_1d,

      -- 7d
      SUM(num_images) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS num_images_7d,
      SUM(num_gifvs) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS num_gifvs_7d,
      SUM(num_videos) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS num_videos_7d,
      SUM(num_audios) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS num_audios_7d,

      -- 30d
      SUM(num_images) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS num_images_30d,
      SUM(num_gifvs) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS num_gifvs_30d,
      SUM(num_videos) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS num_videos_30d,
      SUM(num_audios) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS num_audios_30d
  FROM author_engagement_is_{{ type }}_hourly;

  CREATE SINK IF NOT EXISTS author_engagement_is_{{ type }}_features_sink
  FROM author_engagement_is_{{ type }}_features
  WITH (
      connector='kafka',
      properties.bootstrap.server='${bootstrap_server}',
      topic='author_engagement_is_{{ type }}_features_features',
      primary_key='author_id,event_time',
  ) FORMAT DEBEZIUM ENCODE JSON;
{% endfor %}

{% for media in ['image', 'gifv', 'video'] -%}
  CREATE MATERIALIZED VIEW IF NOT EXISTS author_engagement_has_{{ media }}_hourly AS
  SELECT
    window_start, 
    window_end,
    author_id,
    COUNT(*) FILTER (WHERE type = 'favourite') AS fav_count,
    COUNT(*) FILTER (WHERE type = 'reblog') AS reblogs_count,
    COUNT(*) FILTER (WHERE type = 'reply') AS replies_count,
    SUM(num_mentions) AS num_mentions
  FROM 
    TUMBLE (enriched_status_engagements, event_time, INTERVAL '1 HOUR')
  WHERE has_{{ media }}
  GROUP BY author_id, window_start, window_end;

  CREATE MATERIALIZED VIEW IF NOT EXISTS author_engagement_has_{{ media }}_features AS
  SELECT
      author_id, 
      window_end as event_time,  

      -- 1d
      SUM(fav_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS fav_count_1d,
      SUM(reblogs_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS reblogs_count_1d,
      SUM(replies_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) AS replies_count_1d,

      -- 7d
      SUM(fav_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS fav_count_7d,
      SUM(reblogs_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS reblogs_count_7d,
      SUM(replies_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 6*24 PRECEDING AND CURRENT ROW) AS replies_count_7d,

      -- 30d
      SUM(fav_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS fav_count_30d,
      SUM(reblogs_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS reblogs_count_30d,
      SUM(replies_count) OVER (PARTITION BY author_id ORDER BY window_end ROWS BETWEEN 29*24 PRECEDING AND CURRENT ROW) AS replies_count_30d
  FROM author_engagement_has_{{ media }}_hourly;

  CREATE SINK IF NOT EXISTS author_engagement_has_{{ media }}_features_sink
  FROM author_engagement_has_{{ media }}_features
  WITH (
      connector='kafka',
      properties.bootstrap.server='${bootstrap_server}',
      topic='author_engagement_has_{{ media }}_features_features',
      primary_key='author_id,event_time',
  ) FORMAT DEBEZIUM ENCODE JSON;
{% endfor -%}

-- :down
DROP VIEW IF EXISTS author_engagement_all_hourly;
DROP VIEW IF EXISTS author_engagement_all_features;
DROP SINK IF EXISTS author_engagement_all_sink;

{% for type in ['favourite', 'reblog', 'reply'] -%}
  DROP VIEW IF EXISTS author_engagement_is_{{ type }}_hourly;
  DROP VIEW IF EXISTS author_engagement_is_{{ type }}_features;
  DROP SINK IF EXISTS author_engagement_is_{{ type }}_sink;
{% endfor -%}

{% for media in ['image', 'gifv', 'video'] -%}
  DROP VIEW IF EXISTS author_engagement_has_{{ media }}_hourly;
  DROP VIEW IF EXISTS author_engagement_has_{{ media }}_features;
  DROP SINK IF EXISTS author_engagement_has_{{ media }}_sink;
{% endfor -%}