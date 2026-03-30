// Trending endpoint integration tests require Mastodon tables (statuses,
// accounts, etc.) which don't exist in the fediway-only test database.
// These endpoints work via the CommonFeed provider pipeline, which is
// tested via contract fixtures and the feeds API integration tests.
