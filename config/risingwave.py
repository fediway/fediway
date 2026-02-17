from pydantic import SecretStr, computed_field
from sqlalchemy import URL

from .base import BaseConfig


class RisingWaveConfig(BaseConfig):
    rw_host: str = "localhost"
    rw_port: int = 4566
    rw_user: str = "root"
    rw_pass: SecretStr = ""
    rw_name: str = "dev"

    rw_migrations_table: str = "migrations"

    rw_cdc_host: str | None = None
    rw_cdc_user: str = "risingwave"
    rw_cdc_pass: SecretStr = "password"

    rw_kafka_bootstrap_servers: str = "localhost:9092"

    @property
    def url(self):
        return URL.create(
            "postgresql",
            username=self.rw_user,
            password=self.rw_pass.get_secret_value(),
            host=self.rw_host,
            database=self.rw_name,
            port=self.rw_port,
        )

    @computed_field
    @property
    def rw_migrations_paths(self) -> list[str]:
        """Compute migration paths based on enabled sources."""
        from . import config

        paths = {
            "migrations/risingwave/00_base",
            "migrations/risingwave/02_engagement",
        }

        if config.fediway.kafka_enabled:
            paths.add("migrations/risingwave/01_feed")
            paths.add("migrations/risingwave/07_sinks")

        home = config.feeds.timelines.home.sources

        if home.trending.enabled:
            paths.add("migrations/risingwave/03_trending")

        if config.feeds.trends.tags.enabled:
            paths.add("migrations/risingwave/03_trending")

        if (
            home.top_follows.enabled
            or home.engaged_by_similar_users.enabled
            or home.popular_posts.enabled
        ):
            paths.add("migrations/risingwave/08_affinity")

        if home.engaged_by_friends.enabled:
            paths.add("migrations/risingwave/08_affinity")
            paths.add("migrations/risingwave/10_social_proof")

        if home.tag_affinity.enabled or home.posted_by_friends_of_friends.enabled:
            paths.add("migrations/risingwave/08_affinity")
            paths.add("migrations/risingwave/09_discovery")

        suggestions = config.feeds.suggestions.sources

        if suggestions.similar_interests.enabled or suggestions.popular.enabled:
            paths.add("migrations/risingwave/09_discovery")

        if config.fediway.collaborative_filtering_enabled:
            paths.add("migrations/risingwave/03_collaborative_filtering")

        if config.fediway.features_online_enabled:
            paths.add("migrations/risingwave/04_features_online")

        if config.fediway.features_offline_enabled:
            paths.add("migrations/risingwave/05_features_offline")

        if config.fediway.orbit_enabled:
            paths.add("migrations/risingwave/06_orbit")

        return sorted(paths)
