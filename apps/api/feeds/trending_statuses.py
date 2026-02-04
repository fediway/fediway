from config.algorithm import algorithm_config
from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList


class TrendingStatusesFeed(Feed):
    entity = "status_id"

    def __init__(self, redis=None, rw=None, languages: list[str] | None = None):
        super().__init__()
        self._redis = redis
        self.rw = rw
        self.languages = languages or ["en"]
        self._config = algorithm_config.trends.statuses

    def sources(self) -> dict[str, list[tuple]]:
        from modules.fediway.sources.statuses import TrendingStatusesSource

        cfg = self._config
        sources = {"trending": []}

        for lang in self.languages:
            sources["trending"].append(
                (
                    TrendingStatusesSource(
                        r=self._redis,
                        rw=self.rw,
                        language=lang,
                        top_n=200,
                        max_per_author=cfg.settings.max_per_author,
                    ),
                    50,
                )
            )

        return sources

    def get_min_candidates(self) -> int:
        return 5

    async def forward(self, candidates: CandidateList) -> CandidateList:
        cfg = self._config

        candidates = self.unique(candidates)

        candidates = await self.diversify(
            candidates,
            by="status:author_id",
            penalty=cfg.settings.diversity_penalty,
        )

        candidates = self.sample(candidates, n=cfg.settings.batch_size)

        return candidates
