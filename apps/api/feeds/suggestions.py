from config.algorithm import algorithm_config
from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList


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
        max_per_source = 25

        sources = {
            "social_proof": [],
            "similar": [],
            "popular": [],
        }

        if sources_cfg.social_proof.enabled:
            sources["social_proof"].append(
                (
                    MutualFollowsSource(
                        rw=self.rw,
                        account_id=self.account_id,
                        min_mutual_follows=sources_cfg.social_proof.min_mutual_follows,
                        exclude_following=cfg.settings.exclude_following,
                    ),
                    max_per_source,
                )
            )

        if sources_cfg.similar_interests.enabled:
            sources["similar"].append(
                (
                    SimilarInterestsSource(
                        rw=self.rw,
                        account_id=self.account_id,
                        min_tag_overlap=sources_cfg.similar_interests.min_tag_overlap,
                        exclude_following=cfg.settings.exclude_following,
                    ),
                    max_per_source,
                )
            )

        if sources_cfg.popular.enabled:
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
                    max_per_source,
                )
            )

        return sources

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
