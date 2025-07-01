
-- :up

CREATE TABLE IF NOT EXISTS reports (
    id BIGINT PRIMARY KEY,
    status_ids BIGINT[],
    comment TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    action_taken_by_account_id BIGINT,
    target_account_id BIGINT,
    assigned_account_id BIGINT,
    uri VARCHAR,
    forwarded BOOLEAN,
    category INT,
    action_taken_at TIMESTAMP,
    application_id BIGINT,
) FROM pg_source TABLE 'public.reports';

CREATE INDEX IF NOT EXISTS idx_reports_action_action_taken_by_account_id ON reports(action_taken_by_account_id);
CREATE INDEX IF NOT EXISTS idx_reports_action_target_account_id ON reports(target_account_id);
CREATE INDEX IF NOT EXISTS idx_reports_action_assigned_account_id ON reports(assigned_account_id);

-- :down

DROP INDEX IF EXISTS idx_reports_action_action_taken_by_account_id;
DROP INDEX IF EXISTS idx_reports_action_target_account_id;
DROP INDEX IF EXISTS idx_reports_action_assigned_account_id;

DROP TABLE IF EXISTS reports CASCADE;
