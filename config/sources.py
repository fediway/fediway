from typing import Any

from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    enabled: bool = True
    weight: float = Field(default=0.1, ge=0.0, le=1.0)
    limit: int | None = None
    params: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class SourcesConfig(BaseModel):
    smart_follows: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=True,
            weight=0.35,
            params={
                "max_per_author": 3,
                "recency_half_life_hours": 12,
                "post_window_hours": 48,
                "volume_penalty_threshold": 5,
            },
        ),
    )

    follows_engaging_now: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=True,
            weight=0.15,
            params={
                "window_hours": 6,
                "min_engagers": 2,
            },
        ),
    )

    tag_affinity: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=True,
            weight=0.15,
            params={
                "max_tags": 50,
                "post_window_hours": 48,
                "in_network_penalty": 0.5,
            },
        ),
    )

    second_degree: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=True,
            weight=0.10,
            params={
                "min_mutual_follows": 2,
                "post_window_hours": 48,
            },
        ),
    )

    collaborative_filtering: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=True,
            weight=0.15,
            params={
                "top_similar_users": 50,
                "post_window_hours": 48,
                "exclude_in_network": True,
            },
        ),
    )

    trending: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=True,
            weight=0.10,
            params={
                "min_engagers": 3,
                "gravity": 1.5,
                "max_per_author": 2,
                "window_hours": 24,
            },
        ),
    )

    recent_from_follows: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=True,
            weight=0.0,
            params={"latest_n_per_account": 3},
        ),
    )

    community_recommendations: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=False,
            weight=0.0,
            params={},
        ),
    )

    model_config = {"extra": "allow"}

    def get_enabled_sources(self) -> dict[str, SourceConfig]:
        return {
            name: cfg
            for name, cfg in self.model_dump().items()
            if isinstance(cfg, dict) and cfg.get("enabled", False)
        }

    def get_group_weights(self) -> dict[str, float]:
        group_mapping = {
            "smart_follows": "in-network",
            "follows_engaging_now": "in-network",
            "recent_from_follows": "in-network",
            "tag_affinity": "discovery",
            "second_degree": "discovery",
            "collaborative_filtering": "discovery",
            "community_recommendations": "discovery",
            "trending": "trending",
        }

        weights: dict[str, float] = {}
        for name, group in group_mapping.items():
            cfg = getattr(self, name, None)
            if cfg and cfg.enabled:
                weights[group] = weights.get(group, 0) + cfg.weight

        return weights

    def get_source_config(self, source_name: str) -> SourceConfig | None:
        return getattr(self, source_name, None)
