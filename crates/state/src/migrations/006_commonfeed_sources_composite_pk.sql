ALTER TABLE commonfeed_sources DROP CONSTRAINT commonfeed_sources_pkey;
ALTER TABLE commonfeed_sources ADD PRIMARY KEY (route, provider_domain, algorithm);
