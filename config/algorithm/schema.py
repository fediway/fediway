"""
TOML configuration schema for fediway algorithms.

This module defines the Pydantic models that validate fediway.toml configuration.
"""

from pydantic import BaseModel, Field, model_validator


class GlobalConfig(BaseModel):
    """Global settings applied to all endpoints."""

    content_age_hours: int = Field(default=48, ge=1, le=168)
    cache_ttl_seconds: int = Field(default=300, ge=0, le=3600)


class SourceConfig(BaseModel):
    """Configuration for a single source."""

    enabled: bool = True
    weight: int = Field(default=50, ge=0, le=100)

    model_config = {"extra": "allow"}


class RankingConfig(BaseModel):
    """Ranking parameters."""

    decay_rate: float = Field(default=0.5, ge=0.1, le=2.0)


class HomeWeights(BaseModel):
    """Weight distribution for home timeline sources."""

    in_network: int = Field(default=50, ge=0, le=100)
    discovery: int = Field(default=35, ge=0, le=100)
    trending: int = Field(default=15, ge=0, le=100)

    @model_validator(mode="after")
    def weights_sum_to_100(self):
        total = self.in_network + self.discovery + self.trending
        if total != 100:
            raise ValueError(f"Weights must sum to 100, got {total}")
        return self


class HomeSettings(BaseModel):
    """Settings for home timeline."""

    max_per_author: int = Field(default=3, ge=1, le=10)
    diversity_penalty: float = Field(default=0.1, ge=0.0, le=1.0)
    batch_size: int = Field(default=20, ge=1, le=100)
    include_replies: bool = True
    include_boosts: bool = True


class HomeSources(BaseModel):
    """Source configurations for home timeline."""

    top_follows: SourceConfig = Field(default_factory=SourceConfig)
    engaged_by_friends: SourceConfig = Field(default_factory=SourceConfig)
    tag_affinity: SourceConfig = Field(default_factory=SourceConfig)
    posted_by_friends_of_friends: SourceConfig = Field(default_factory=SourceConfig)
    trending: SourceConfig = Field(default_factory=SourceConfig)
    engaged_by_similar_users: SourceConfig = Field(
        default_factory=lambda: SourceConfig(enabled=False)
    )

    model_config = {"extra": "forbid"}


class HomeTimelineConfig(BaseModel):
    """Configuration for /api/v1/timelines/home."""

    weights: HomeWeights = Field(default_factory=HomeWeights)
    settings: HomeSettings = Field(default_factory=HomeSettings)
    ranking: RankingConfig = Field(default_factory=RankingConfig)
    sources: HomeSources = Field(default_factory=HomeSources)


class TrendingScoringConfig(BaseModel):
    """Scoring weights for trending."""

    weight_favorites: float = Field(default=1.0, ge=0.0, le=5.0)
    weight_reblogs: float = Field(default=2.0, ge=0.0, le=5.0)
    weight_replies: float = Field(default=1.5, ge=0.0, le=5.0)
    velocity_boost: bool = True


class TrendingFiltersConfig(BaseModel):
    """Filters for trending statuses."""

    exclude_sensitive: bool = False
    exclude_replies: bool = True
    exclude_boosts: bool = True
    min_account_age_days: int = Field(default=7, ge=0, le=365)


class TrendingStatusesSettings(BaseModel):
    """Settings for trending statuses."""

    window_hours: int = Field(default=24, ge=1, le=168)
    max_per_author: int = Field(default=2, ge=1, le=10)
    min_engagement: int = Field(default=5, ge=1, le=100)
    local_only: bool = False
    batch_size: int = Field(default=20, ge=1, le=100)
    diversity_penalty: float = Field(default=0.1, ge=0.0, le=1.0)


class TrendingStatusesConfig(BaseModel):
    """Configuration for /api/v1/trends/statuses."""

    settings: TrendingStatusesSettings = Field(default_factory=TrendingStatusesSettings)
    scoring: TrendingScoringConfig = Field(default_factory=TrendingScoringConfig)
    filters: TrendingFiltersConfig = Field(default_factory=TrendingFiltersConfig)


class TrendingTagsScoringConfig(BaseModel):
    """Scoring for trending tags."""

    weight_posts: float = Field(default=1.0, ge=0.0, le=5.0)
    weight_accounts: float = Field(default=2.0, ge=0.0, le=5.0)
    velocity_boost: bool = True


class TrendingTagsFiltersConfig(BaseModel):
    """Filters for trending tags."""

    blocked_tags: list[str] = Field(default_factory=list)


class TrendingTagsSettings(BaseModel):
    """Settings for trending tags."""

    window_hours: int = Field(default=24, ge=1, le=168)
    min_posts: int = Field(default=3, ge=1, le=50)
    min_accounts: int = Field(default=2, ge=1, le=20)
    max_results: int = Field(default=20, ge=1, le=50)
    local_only: bool = False


class TrendingTagsConfig(BaseModel):
    """Configuration for /api/v1/trends/tags."""

    settings: TrendingTagsSettings = Field(default_factory=TrendingTagsSettings)
    scoring: TrendingTagsScoringConfig = Field(default_factory=TrendingTagsScoringConfig)
    filters: TrendingTagsFiltersConfig = Field(default_factory=TrendingTagsFiltersConfig)


class TrendingConfig(BaseModel):
    """Container for all trending configs."""

    statuses: TrendingStatusesConfig = Field(default_factory=TrendingStatusesConfig)
    tags: TrendingTagsConfig = Field(default_factory=TrendingTagsConfig)


class SuggestionsWeights(BaseModel):
    """Weight distribution for suggestion sources."""

    social_proof: int = Field(default=40, ge=0, le=100)
    similar_interests: int = Field(default=35, ge=0, le=100)
    popular: int = Field(default=25, ge=0, le=100)

    @model_validator(mode="after")
    def weights_sum_to_100(self):
        total = self.social_proof + self.similar_interests + self.popular
        if total != 100:
            raise ValueError(f"Weights must sum to 100, got {total}")
        return self


class SuggestionsSettings(BaseModel):
    """Settings for follow suggestions."""

    max_results: int = Field(default=40, ge=1, le=100)
    exclude_following: bool = True
    min_account_age_days: int = Field(default=7, ge=0, le=365)


class SuggestionsSocialProofConfig(BaseModel):
    """Social proof source config."""

    enabled: bool = True
    min_mutual_follows: int = Field(default=2, ge=1, le=20)


class SuggestionsSimilarInterestsConfig(BaseModel):
    """Similar interests source config."""

    enabled: bool = True
    min_tag_overlap: int = Field(default=3, ge=1, le=20)


class SuggestionsPopularConfig(BaseModel):
    """Popular accounts source config."""

    enabled: bool = True
    local_only: bool = True
    min_followers: int = Field(default=10, ge=1, le=1000)


class SuggestionsSourcesConfig(BaseModel):
    """Source configurations for suggestions."""

    social_proof: SuggestionsSocialProofConfig = Field(default_factory=SuggestionsSocialProofConfig)
    similar_interests: SuggestionsSimilarInterestsConfig = Field(
        default_factory=SuggestionsSimilarInterestsConfig
    )
    popular: SuggestionsPopularConfig = Field(default_factory=SuggestionsPopularConfig)


class SuggestionsConfig(BaseModel):
    """Configuration for /api/v2/suggestions."""

    settings: SuggestionsSettings = Field(default_factory=SuggestionsSettings)
    weights: SuggestionsWeights = Field(default_factory=SuggestionsWeights)
    sources: SuggestionsSourcesConfig = Field(default_factory=SuggestionsSourcesConfig)


class TimelinesConfig(BaseModel):
    """Container for timeline configs."""

    home: HomeTimelineConfig = Field(default_factory=HomeTimelineConfig)


class FediwayTomlConfig(BaseModel):
    """
    Root configuration model for fediway.toml.

    Maps directly to Mastodon API endpoints:
    - [timelines.home] -> GET /api/v1/timelines/home
    - [trends.statuses] -> GET /api/v1/trends/statuses
    - [trends.tags] -> GET /api/v1/trends/tags
    - [suggestions] -> GET /api/v2/suggestions
    """

    timelines: TimelinesConfig = Field(default_factory=TimelinesConfig)
    trends: TrendingConfig = Field(default_factory=TrendingConfig)
    suggestions: SuggestionsConfig = Field(default_factory=SuggestionsConfig)

    # Note: 'global' is a Python keyword, so we use alias
    global_settings: GlobalConfig = Field(default_factory=GlobalConfig, alias="global")

    model_config = {"populate_by_name": True}
