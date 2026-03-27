CREATE TABLE orbit_user_vectors (
    account_id          BIGINT PRIMARY KEY,
    vector              FLOAT4[] NOT NULL,
    engagement_count    BIGINT NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE orbit_cursors (
    source_name         TEXT PRIMARY KEY,
    last_id             BIGINT NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE commonfeed_capabilities
    ADD COLUMN embedding_required   BOOLEAN,
    ADD COLUMN embedding_models     JSONB;
