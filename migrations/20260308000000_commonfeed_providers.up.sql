CREATE TABLE commonfeed_providers (
    domain              TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    status              TEXT CHECK (status IN ('pending', 'approved', 'failed')),
    enabled             BOOLEAN NOT NULL DEFAULT true,
    base_url            TEXT NOT NULL,
    max_results         INTEGER NOT NULL CHECK (max_results > 0),
    api_key             TEXT,
    request_id          TEXT,
    verify_path         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE commonfeed_capabilities (
    provider_domain     TEXT NOT NULL REFERENCES commonfeed_providers(domain) ON DELETE CASCADE,
    resource            TEXT NOT NULL,
    algorithm           TEXT NOT NULL,
    description         TEXT NOT NULL,
    filters             TEXT[] NOT NULL DEFAULT '{}',
    enabled             BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (provider_domain, resource, algorithm)
);
