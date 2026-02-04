from config.algorithm import algorithm_config
from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList
from modules.fediway.feed.sampling import WeightedGroupSampler


class HomeFeed(Feed):
    entity = "status_id"

    def __init__(
        self,
        account_id: int,
        rw=None,
        redis=None,
        feature_service=None,
        languages: list[str] | None = None,
    ):
        super().__init__(feature_service=feature_service)
        self.account_id = account_id
        self.rw = rw
        self._redis = redis
        self.languages = languages or ["en"]
        self._config = algorithm_config.home

    def sources(self) -> dict[str, list[tuple]]:
        from modules.fediway.sources.statuses import (
            FollowsEngagingNowSource,
            SecondDegreeSource,
            SmartFollowsSource,
            TagAffinitySource,
            TrendingStatusesSource,
        )

        cfg = self._config
        max_candidates = 500

        w = cfg.weights
        w_in = w.in_network if w else 50
        w_disc = w.discovery if w else 35
        w_trend = w.trending if w else 15

        sources = {
            "in-network": [],
            "discovery": [],
            "trending": [],
            "_fallback": [],
        }

        if cfg.sources.smart_follows.enabled:
            n = int(max_candidates * w_in / 100 * 0.6)
            sources["in-network"].append(
                (
                    SmartFollowsSource(
                        rw=self.rw,
                        account_id=self.account_id,
                        max_per_author=cfg.settings.max_per_author,
                    ),
                    n,
                )
            )

        if cfg.sources.follows_engaging.enabled:
            n = int(max_candidates * w_in / 100 * 0.4)
            sources["in-network"].append(
                (
                    FollowsEngagingNowSource(
                        rw=self.rw,
                        account_id=self.account_id,
                    ),
                    n,
                )
            )

        if cfg.sources.tag_affinity.enabled:
            n = int(max_candidates * w_disc / 100 * 0.5)
            sources["discovery"].append(
                (
                    TagAffinitySource(
                        rw=self.rw,
                        account_id=self.account_id,
                    ),
                    n,
                )
            )

        if cfg.sources.second_degree.enabled:
            n = int(max_candidates * w_disc / 100 * 0.5)
            sources["discovery"].append(
                (
                    SecondDegreeSource(
                        rw=self.rw,
                        account_id=self.account_id,
                    ),
                    n,
                )
            )

        if cfg.sources.trending.enabled:
            n = int(max_candidates * w_trend / 100)
            for lang in self.languages:
                sources["trending"].append(
                    (
                        TrendingStatusesSource(
                            r=self._redis,
                            rw=self.rw,
                            language=lang,
                        ),
                        n // len(self.languages),
                    )
                )

        for lang in self.languages:
            sources["_fallback"].append(
                (
                    TrendingStatusesSource(
                        r=self._redis,
                        rw=self.rw,
                        language=lang,
                        top_n=200,
                    ),
                    40 // len(self.languages),
                )
            )

        return sources

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

        candidates = self.sample(
            candidates,
            n=cfg.settings.batch_size,
            sampler=WeightedGroupSampler(self._get_group_weights()),
        )

        return candidates
