-- Mastodon provides this function; we define it here for standalone testing.
CREATE OR REPLACE FUNCTION timestamp_id(table_name text) RETURNS bigint AS $$
DECLARE
    time_part bigint;
    tail bigint;
BEGIN
    time_part := (date_part('epoch', now()) * 1000)::bigint << 16;
    tail := nextval(table_name || '_id_seq') & 65535;
    RETURN time_part | tail;
END;
$$ LANGUAGE plpgsql VOLATILE;
