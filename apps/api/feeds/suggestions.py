from config.algorithm import algorithm_config
from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList
from modules.fediway.feed.sampling import WeightedGroupSampler


class SuggestionsFeed(Feed):
    entity = "account_id"

    def __init__(self, account_id: int, rw=None):
        super().__init__()
        self.account_id = account_id
        self.rw = rw
        self._config = algorithm_config.suggestions

    def sources(self) -> dict[str, list[tuple]]:
        from modules.fediway.sources.accounts import (
            MutualFollowsSource,
            PopularAccountsSource,
            SimilarInterestsSource,
        )

        cfg = self._config
        sources_cfg = cfg.sources
        max_results = cfg.settings.max_results

        sources = {
            "social_proof": [],
            "similar": [],
            "popular": [],
        }

        if sources_cfg.social_proof.enabled:
            n = int(max_results * self._get_weight("social_proof"))
            sources["social_proof"].append(
                (
                    MutualFollowsSource(
                        rw=self.rw,
                        account_id=self.account_id,
                        min_mutual_follows=sources_cfg.social_proof.min_mutual_follows,
                        exclude_following=cfg.settings.exclude_following,
                    ),
                    n,
                )
            )

        if sources_cfg.similar_interests.enabled:
            n = int(max_results * self._get_weight("similar"))
            sources["similar"].append(
                (
                    SimilarInterestsSource(
                        rw=self.rw,
                        account_id=self.account_id,
                        min_tag_overlap=sources_cfg.similar_interests.min_tag_overlap,
                        exclude_following=cfg.settings.exclude_following,
                    ),
                    n,
                )
            )

        if sources_cfg.popular.enabled:
            n = int(max_results * self._get_weight("popular"))
            sources["popular"].append(
                (
                    PopularAccountsSource(
                        rw=self.rw,
                        account_id=self.account_id,
                        min_followers=sources_cfg.popular.min_followers,
                        local_only=sources_cfg.popular.local_only,
                        exclude_following=cfg.settings.exclude_following,
                        min_account_age_days=cfg.settings.min_account_age_days,
                    ),
                    n,
                )
            )

        return sources

    def _get_weight(self, group: str) -> float:
        w = self._config.weights
        if not w:
            defaults = {"social_proof": 40, "similar": 35, "popular": 25}
            return defaults.get(group, 0) / 100

        mapping = {
            "social_proof": w.social_proof,
            "similar": w.similar_interests,
            "popular": w.popular,
        }
        return mapping.get(group, 0) / 100

    def get_min_candidates(self) -> int:
        return 5

    def _get_group_weights(self) -> dict[str, float]:
        return {
            "social_proof": self._get_weight("social_proof"),
            "similar": self._get_weight("similar"),
            "popular": self._get_weight("popular"),
        }

    async def forward(self, candidates: CandidateList) -> CandidateList:
        cfg = self._config

        candidates = self.unique(candidates)

        candidates = self.sample(
            candidates,
            n=cfg.settings.max_results,
            sampler=WeightedGroupSampler(self._get_group_weights()),
        )

        return candidates
