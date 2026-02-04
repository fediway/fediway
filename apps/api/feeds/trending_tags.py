from config.algorithm import algorithm_config
from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList


class TrendingTagsFeed(Feed):
    entity = "tag_id"

    def __init__(self, redis=None, rw=None):
        super().__init__()
        self._redis = redis
        self.rw = rw
        self._config = algorithm_config.trends.tags

    def sources(self) -> dict[str, list[tuple]]:
        from modules.fediway.sources.tags import TrendingTagsSource

        cfg = self._config
        sources = {"trending": []}

        sources["trending"].append(
            (
                TrendingTagsSource(
                    r=self._redis,
                    rw=self.rw,
                    window_hours=cfg.settings.window_hours,
                    min_posts=cfg.settings.min_posts,
                    min_accounts=cfg.settings.min_accounts,
                    local_only=cfg.settings.local_only,
                    weight_posts=cfg.scoring.weight_posts,
                    weight_accounts=cfg.scoring.weight_accounts,
                    velocity_boost=cfg.scoring.velocity_boost,
                    blocked_tags=cfg.filters.blocked_tags,
                ),
                100,
            )
        )

        return sources

    def get_min_candidates(self) -> int:
        return 5

    async def forward(self, candidates: CandidateList) -> CandidateList:
        cfg = self._config

        candidates = self.unique(candidates)

        candidates = self.sample(candidates, n=cfg.settings.max_results)

        return candidates
