from config.algorithm import algorithm_config
from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList
from modules.fediway.sources import Source


class TrendingStatusesFeed(Feed):
    entity = "status_id"

    def __init__(
        self,
        sources: dict[str, list[tuple[Source, int]]],
    ):
        super().__init__()
        self._sources = sources
        self._config = algorithm_config.trends.statuses

    def sources(self) -> dict[str, list[tuple]]:
        return self._sources

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
