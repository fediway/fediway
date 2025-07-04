
-- :up

ALTER SYSTEM SET bypass_cluster_limits TO true;

-- :down

ALTER SYSTEM SET bypass_cluster_limits TO false;