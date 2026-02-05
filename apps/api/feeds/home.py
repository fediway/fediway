from config import config
from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList
from modules.fediway.sources import Source


class HomeFeed(Feed):
    entity = "status_id"

    def __init__(
        self,
        account_id: int,
        sources: dict[str, list[tuple[Source, int]]],
        feature_service=None,
    ):
        super().__init__(feature_service=feature_service)
        self.account_id = account_id
        self._sources = sources
        self._config = config.feeds.timelines.home

    def sources(self) -> dict[str, list[tuple]]:
        return self._sources

    def get_min_candidates(self) -> int:
        return self._config.settings.batch_size

    def _get_group_weights(self) -> dict[str, float]:
        w = self._config.weights
        w_in = w.in_network if w else 50
        w_disc = w.discovery if w else 35
        w_trend = w.trending if w else 15

        return {
            "in-network": w_in / 100,
            "discovery": w_disc / 100,
            "trending": w_trend / 100,
            "fallback": 0.1,
        }

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
