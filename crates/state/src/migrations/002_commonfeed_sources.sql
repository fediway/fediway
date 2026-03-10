CREATE TABLE commonfeed_sources (
    route               TEXT NOT NULL,          -- fediway route: timelines/tag, trends/statuses, trends/tags
    provider_domain     TEXT NOT NULL REFERENCES commonfeed_providers(domain) ON DELETE CASCADE,
    resource            TEXT NOT NULL,           -- capability resource: posts, tags, links
    algorithm           TEXT NOT NULL,           -- capability algorithm: hot, trending
    enabled             BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (route, provider_domain),
    FOREIGN KEY (provider_domain, resource, algorithm)
        REFERENCES commonfeed_capabilities(provider_domain, resource, algorithm) ON DELETE CASCADE
);
