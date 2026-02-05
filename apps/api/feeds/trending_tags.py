from config import config
from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList
from modules.fediway.sources import Source


class TrendingTagsFeed(Feed):
    entity = "tag_id"

    def __init__(
        self,
        sources: dict[str, list[tuple[Source, int]]],
    ):
        super().__init__()
        self._sources = sources
        self._config = config.feeds.trends.tags

    def sources(self) -> dict[str, list[tuple]]:
        return self._sources

    def get_min_candidates(self) -> int:
        return 5

    async def forward(self, candidates: CandidateList) -> CandidateList:
        cfg = self._config

        candidates = self.unique(candidates)

        candidates = self.sample(candidates, n=cfg.settings.max_results)

        return candidates
