import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np

from .candidates import CandidateList
from .pipeline import Pipeline
from .sampling import InverseTransformSampler, Sampler, WeightedGroupSampler

if TYPE_CHECKING:
    from ..sources import Source

logger = logging.getLogger(__name__)

# State bounds to prevent unbounded growth
MAX_SEEN_ITEMS = 500
MAX_REMEMBERED_ITEMS = 200


class Feed(ABC):
    entity: str = "status_id"

    def __init__(self, feature_service=None):
        self._feature_service = feature_service
        self._pipeline: Pipeline | None = None
        self._config = None
        self._remembered = CandidateList(self.entity)
        self._seen: set = set()
        self._heuristic_states: dict = {}

    @abstractmethod
    def sources(self) -> dict[str, list[tuple["Source", int]]]:
        # Return dict mapping group names to list of (Source, limit) tuples.
        # Special group "_fallback" is used when main sources yield too few results.
        pass

    @abstractmethod
    async def forward(self, candidates: CandidateList) -> CandidateList:
        pass

    def get_min_candidates(self) -> int:
        return 10

    def _get_group_weights(self) -> dict[str, float]:
        """Return group weights for sampling. Override in subclass."""
        return {}

    def _get_sampler(self) -> Sampler:
        """Return appropriate sampler based on group structure.

        - Multiple groups: WeightedGroupSampler (balances across groups)
        - Single/no groups: InverseTransformSampler (score-weighted random)
        """
        weights = self._get_group_weights()
        if len(weights) > 1:
            return WeightedGroupSampler(weights)
        return InverseTransformSampler()

    @property
    def pipeline(self) -> Pipeline | None:
        return self._pipeline

    def _validate_sources(self, source_groups: dict) -> None:
        if not isinstance(source_groups, dict):
            raise TypeError(
                f"{self.__class__.__name__}.sources() must return dict, "
                f"got {type(source_groups).__name__}"
            )

        for group, items in source_groups.items():
            if not isinstance(items, list):
                raise TypeError(
                    f"sources()['{group}'] must be list of (Source, int) tuples, "
                    f"got {type(items).__name__}"
                )
            for i, item in enumerate(items):
                if not isinstance(item, tuple) or len(item) != 2:
                    raise TypeError(f"sources()['{group}'][{i}] must be (Source, int) tuple")

    def _build_pipeline(self) -> Pipeline:
        pipeline = Pipeline(self._feature_service)
        pipeline.select(self.entity)

        source_groups = self.sources()
        self._validate_sources(source_groups)

        for group, sources_with_limits in source_groups.items():
            if group.startswith("_"):
                continue
            for source, limit in sources_with_limits:
                pipeline.source(source, limit, group=group)

        return pipeline

    async def _collect_sources(self) -> CandidateList:
        candidates = CandidateList(self.entity)

        try:
            if self._pipeline is None:
                self._pipeline = self._build_pipeline()

            for step in self._pipeline.steps:
                try:
                    candidates = await step(candidates)
                except Exception as e:
                    logger.warning(f"Source step failed: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Pipeline construction failed: {e}", exc_info=True)

        return candidates

    async def _collect_fallback(self) -> CandidateList:
        source_groups = self.sources()
        fallback = source_groups.get("_fallback", [])

        if not fallback:
            return CandidateList(self.entity)

        async def collect_one(source, limit):
            result = CandidateList(self.entity)
            try:
                collected = source.collect(limit)
                if hasattr(collected, "__aiter__"):
                    async for c in collected:
                        if c not in self._seen:
                            result.append(c, source=source.id, source_group="fallback")
                else:
                    for c in collected:
                        if c not in self._seen:
                            result.append(c, source=source.id, source_group="fallback")
            except Exception as e:
                logger.warning(f"Fallback source {source.id} failed: {e}")
            return result

        results = await asyncio.gather(*[collect_one(source, limit) for source, limit in fallback])

        combined = CandidateList(self.entity)
        for result in results:
            combined += result

        return combined

    def is_new(self) -> bool:
        """Check if this feed has no cached candidates."""
        return len(self._remembered) == 0

    def get_state(self) -> dict:
        """Get serializable state for persistence."""
        return {
            "seen": list(self._seen),
            "remembered": self._remembered.get_state(),
            "heuristics": self._heuristic_states,
        }

    def set_state(self, state: dict) -> None:
        """Restore state from persistence."""
        self._seen = set(state.get("seen", []))
        remembered_state = state.get("remembered")
        if remembered_state:
            self._remembered.set_state(remembered_state)
        self._heuristic_states = state.get("heuristics", {})

    async def collect(self) -> None:
        """Collect new candidates from sources.

        This is called:
        1. On first request when no cached state exists
        2. In background after serving results to prefetch for next request
        """
        candidates = await self._collect_sources()

        if len(candidates) < self.get_min_candidates():
            fallback_candidates = await self._collect_fallback()
            candidates += fallback_candidates

        candidates = self._remove_seen(candidates)
        candidates = await self.forward(candidates)

        if candidates is None:
            raise RuntimeError(
                f"{self.__class__.__name__}.forward() returned None. "
                "Did you forget to return candidates?"
            )

        self._remembered += candidates
        self._trim_state()

    async def execute(
        self,
        max_id: int | None = None,
        offset: int | None = None,
        limit: int = 20,
    ) -> CandidateList:
        """Execute feed and return paginated results.

        Flow:
        1. If no cached candidates, collect from sources
        2. Return paginated slice from _remembered
        3. Mark returned items as seen

        State persistence is handled by FeedEngine.
        """
        if self.is_new():
            await self.collect()

        results = self._paginate(max_id=max_id, offset=offset, limit=limit)

        for c in results:
            self._seen.add(c.id)

        return results

    def unique(self, candidates: CandidateList) -> CandidateList:
        if len(candidates) == 0:
            return candidates
        _, indices = np.unique(candidates.get_candidates(), return_index=True)
        indices = np.sort(indices)
        return candidates[indices]

    def _remove_seen(self, candidates: CandidateList) -> CandidateList:
        if not self._seen:
            return candidates
        mask = np.array([c not in self._seen for c in candidates.get_candidates()])
        return candidates[mask]

    async def rank(self, candidates: CandidateList, ranker=None) -> CandidateList:
        if ranker is None or self._feature_service is None:
            return candidates

        if len(candidates) == 0:
            return candidates

        entity_rows = candidates.get_entity_rows()
        features = await self._feature_service.get(entity_rows, ranker.features)
        scores = ranker.predict(features)
        candidates.set_scores(scores)

        return candidates

    async def diversify(
        self, candidates: CandidateList, by: str, penalty: float = 0.1
    ) -> CandidateList:
        from ..heuristics import DiversifyHeuristic

        if len(candidates) == 0:
            return candidates

        heuristic_key = f"diversify:{by}"
        if heuristic_key in self._heuristic_states:
            heuristic = DiversifyHeuristic(by, penalty)
            heuristic.set_state(self._heuristic_states[heuristic_key])
        else:
            heuristic = DiversifyHeuristic(by, penalty)

        if self._feature_service is None:
            return candidates

        try:
            entity_rows = candidates.get_entity_rows()
            features = await self._feature_service.get(entity_rows, heuristic.features)
            adjusted_scores = heuristic(candidates, features)
            candidates.set_scores(adjusted_scores)
        except Exception as e:
            logger.warning(f"Feature fetch failed for diversify: {e}")

        self._heuristic_states[heuristic_key] = heuristic.get_state()

        return candidates

    def sample(
        self,
        candidates: CandidateList,
        n: int,
        sampler: Sampler | None = None,
    ) -> CandidateList:
        if sampler is None:
            sampler = self._get_sampler()

        if len(candidates) == 0:
            return candidates

        sampled = CandidateList(candidates.entity)
        remaining = candidates.copy()

        for _ in range(min(n, len(candidates))):
            if len(remaining) == 0:
                break

            idx = sampler.sample(remaining)
            if idx is None:
                break

            sampled.append(remaining[idx])
            remaining.remove_at(idx)

        return sampled

    def _trim_state(self):
        """Trim state to prevent unbounded growth."""
        if len(self._seen) > MAX_SEEN_ITEMS:
            seen_list = list(self._seen)
            self._seen = set(seen_list[-MAX_SEEN_ITEMS:])

        if len(self._remembered) > MAX_REMEMBERED_ITEMS:
            self._remembered = self._remembered[-MAX_REMEMBERED_ITEMS:]

    def _paginate(self, max_id: int | None, offset: int | None, limit: int) -> CandidateList:
        if len(self._remembered) == 0:
            return CandidateList(self.entity)

        if max_id is not None:
            try:
                start = self._remembered.index(max_id) + 1
            except ValueError:
                return CandidateList(self.entity)
            return self._remembered[start : start + limit]

        if offset is not None and offset > 0:
            return self._remembered[offset : offset + limit]

        return self._remembered[:limit]

    def flush(self):
        """Clear all local state."""
        self._seen = set()
        self._remembered = CandidateList(self.entity)
        self._heuristic_states = {}
