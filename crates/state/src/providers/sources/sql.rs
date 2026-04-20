pub(super) const SOURCES_QUERY: &str = r"
    SELECT p.domain, p.base_url, p.api_key, p.max_results, c.filters, b.algorithm
    FROM commonfeed_sources b
    JOIN commonfeed_providers p ON p.domain = b.provider_domain
    JOIN commonfeed_capabilities c ON c.provider_domain = b.provider_domain
        AND c.resource = b.resource AND c.algorithm = b.algorithm
    WHERE b.route = $1 AND b.enabled = true
      AND p.status = 'approved' AND p.enabled = true
";
