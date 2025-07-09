
-- :up

CREATE TABLE IF NOT EXISTS statuses (
    id BIGINT PRIMARY KEY,
    uri VARCHAR,
    text TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    in_reply_to_id BIGINT,
    reblog_of_id BIGINT,
    url VARCHAR,
    sensitive BOOLEAN,
    visibility INT,
    spoiler_text TEXT,
    reply BOOLEAN,
    language VARCHAR,
    conversation_id BIGINT,
    local BOOLEAN,
    account_id BIGINT,
    application_id BIGINT,
    in_reply_to_account_id BIGINT,
    poll_id BIGINT,
    deleted_at TIMESTAMP,
    edited_at TIMESTAMP
) FROM pg_source TABLE 'public.statuses';

CREATE INDEX IF NOT EXISTS idx_statuses_reblog_of_id ON statuses(reblog_of_id);
CREATE INDEX IF NOT EXISTS idx_statuses_in_reply_to_id ON statuses(in_reply_to_id); 
CREATE INDEX IF NOT EXISTS idx_statuses_in_reply_to_account_id ON statuses(in_reply_to_account_id); 
CREATE INDEX IF NOT EXISTS idx_statuses_created_at ON statuses(created_at); 
CREATE INDEX IF NOT EXISTS idx_statuses_language ON statuses(language); 

CREATE TABLE IF NOT EXISTS statuses_tags (
    status_id BIGINT,
    tag_id BIGINT,
    PRIMARY KEY (status_id, tag_id)
) FROM pg_source TABLE 'public.statuses_tags';

CREATE INDEX IF NOT EXISTS idx_statuses_tags_status_id ON statuses_tags(status_id);
CREATE INDEX IF NOT EXISTS idx_statuses_tags_tag_id ON statuses_tags(tag_id);

CREATE TABLE IF NOT EXISTS status_pins (
    id BIGINT PRIMARY KEY,
    account_id BIGINT,
    status_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) FROM pg_source TABLE 'public.status_pins';

CREATE INDEX IF NOT EXISTS idx_status_pins_account_id ON status_pins(account_id);
CREATE INDEX IF NOT EXISTS idx_status_pins_status_id ON status_pins(status_id);

CREATE TABLE IF NOT EXISTS status_stats (
    id BIGINT PRIMARY KEY,
    status_id BIGINT,
    reblogs_count BIGINT,
    favourites_count BIGINT,
    replies_count BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) FROM pg_source TABLE 'public.status_stats';

CREATE INDEX IF NOT EXISTS idx_status_id_status_id ON status_stats(status_id);

CREATE SINK IF NOT EXISTS status_stats_sink AS
SELECT 
  status_id,
  favourites_count,
  reblogs_count,
  replies_count,
  updated_at AS event_time
FROM status_stats st
WHERE created_at > NOW() - INTERVAL '30 DAYS'
WITH (
  connector='kafka',
  properties.bootstrap.server='{{ bootstrap_server }}',
  topic='status_stats',
  primary_key='status_id',
  properties.linger.ms='1000',
) FORMAT PLAIN ENCODE JSON (
  force_append_only='true'
);

CREATE TABLE IF NOT EXISTS offline_features_status_stats (
    status_id BIGINT,
    event_time TIMESTAMP,
    favourites_count BIGINT,
    reblogs_count BIGINT,
    replies_count BIGINT,
    PRIMARY KEY (status_id, event_time)
) APPEND ONLY ON CONFLICT IGNORE WITH (
    connector='kafka',
    topic='offline_features_status_stats',
    properties.bootstrap.server='{{ bootstrap_server }}',
) FORMAT PLAIN ENCODE JSON;

-- :down

DROP SINK IF EXISTS status_stats_sink;

DROP INDEX IF EXISTS idx_status_pins_account_id;
DROP INDEX IF EXISTS idx_status_pins_status_id;
DROP INDEX IF EXISTS idx_statuses_reblog_of_id;
DROP INDEX IF EXISTS idx_statuses_in_reply_to_id;
DROP INDEX IF EXISTS idx_statuses_in_reply_to_account_id;
DROP INDEX IF EXISTS idx_statuses_created_at;
DROP INDEX IF EXISTS idx_statuses_language;
DROP INDEX IF EXISTS idx_status_id_status_id;
DROP INDEX IF EXISTS idx_statuses_tags_status_id;
DROP INDEX IF EXISTS idx_statuses_tags_tag_id;

DROP TABLE IF EXISTS status_pins CASCADE;
DROP TABLE IF EXISTS status_stats CASCADE;
DROP TABLE IF EXISTS statuses_tags CASCADE;
DROP TABLE IF EXISTS statuses CASCADE;
DROP TABLE IF EXISTS offline_features_status_stats CASCADE;