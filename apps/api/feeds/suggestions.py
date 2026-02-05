from config.algorithm import algorithm_config
from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList
from modules.fediway.sources import Source


class SuggestionsFeed(Feed):
    entity = "account_id"

    def __init__(
        self,
        account_id: int,
        sources: dict[str, list[tuple[Source, int]]],
    ):
        super().__init__()
        self.account_id = account_id
        self._sources = sources
        self._config = algorithm_config.suggestions

    def sources(self) -> dict[str, list[tuple]]:
        return self._sources

    def get_min_candidates(self) -> int:
        return 5

    def _get_group_weights(self) -> dict[str, float]:
        w = self._config.weights
        w_social = w.social_proof if w else 40
        w_similar = w.similar_interests if w else 35
        w_popular = w.popular if w else 25

        return {
            "social_proof": w_social / 100,
            "similar": w_similar / 100,
            "popular": w_popular / 100,
        }

    async def forward(self, candidates: CandidateList) -> CandidateList:
        cfg = self._config

        candidates = self.unique(candidates)

        candidates = self.sample(candidates, n=cfg.settings.max_results)

        return candidates
