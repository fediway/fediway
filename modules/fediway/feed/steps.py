import asyncio
import time
from copy import deepcopy

import numpy as np
import pandas as pd

from shared.utils.logging import log_debug, log_error, log_warning

from ..heuristics import Heuristic
from ..rankers import Ranker
from ..sources import Source
from .candidates import CandidateList
from .features import Features
from .sampling import Sampler


class PipelineStep:
    def results(self) -> CandidateList:
        raise NotImplementedError

    def get_params(self):
        return {}

    def get_state(self):
        return None

    def set_state(self, state):
        pass

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        raise NotImplementedError


class RankingStep(PipelineStep):
    def __init__(self, ranker: Ranker, feature_service: Features, entity: str):
        self.ranker = ranker
        self.feature_service = feature_service
        self.entity = entity
        self._features = pd.DataFrame([])
        self._feature_retrieval_duration = 0
        self._ranking_duration = 0
        self._scores = np.array([])
        self._candidates = []

    def get_feature_retrieval_duration(self) -> int:
        return self._feature_retrieval_duration

    def get_ranking_duration(self) -> int:
        return self._ranking_duration

    def get_features(self) -> pd.DataFrame:
        return self._features

    def get_candidates(self) -> list:
        return self._candidates

    def get_scores(self) -> np.ndarray:
        return self._scores

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        if len(candidates) == 0:
            return candidates

        start_time = time.perf_counter_ns()
        entities = candidates.get_entity_rows()

        X = await self.feature_service.get(entities, self.ranker.features)
        self._feature_retrieval_duration = time.perf_counter_ns() - start_time

        start_time = time.perf_counter_ns()
        scores = self.ranker.predict(X)
        self._ranking_duration = time.perf_counter_ns() - start_time

        log_debug(
            "Ranked candidates",
            module="feed",
            ranker=self.ranker.id,
            count=len(candidates),
            duration_ms=round(self._ranking_duration / 1_000_000, 2),
        )

        self._features = X
        self._candidates = candidates
        self._scores = scores

        candidates.set_scores(scores)

        return candidates


class RememberStep(PipelineStep):
    def __init__(self, entity):
        self.candidates = CandidateList(entity)

    def get_state(self):
        return {
            "candidates": self.candidates.get_state(),
        }

    def set_state(self, state):
        if "candidates" not in self.candidates:
            return
        self.candidates.set_state(state["candidates"])

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        self.candidates += candidates

        return self.candidates


class PaginationStep(PipelineStep):
    def __init__(self, entity: str, limit: int, offset: int = 0, max_id: int | None = None):
        self.entity = entity
        self.candidates = CandidateList(entity)
        self.limit = max(limit, 0)
        self.offset = max(offset, 0)
        self.max_id = max_id

    def get_params(self):
        return {
            "limit": self.limit,
            "offset": self.offset,
            "max_id": self.max_id,
        }

    def get_state(self):
        return {"candidates": self.candidates.get_state()}

    def set_state(self, state):
        if "candidates" not in state:
            log_warning("Candidates missing in state", module="feed")
            return
        self.candidates.set_state(state["candidates"])

    def results(self):
        start = 0

        if self.max_id is not None:
            try:
                start = self.candidates.index(self.max_id) + 1
            except ValueError:
                log_warning("Missing candidate", module="feed", max_id=self.max_id)
                return CandidateList(self.entity)
        elif self.offset is not None:
            start = self.offset

        end = start + self.limit

        return self.candidates[start:end]

    def __len__(self) -> int:
        return len(self.candidates)

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        self.candidates += candidates

        return self.results()


class SourcingStep(PipelineStep):
    def __init__(self, group: str | None = None):
        self.collected = set()
        self.sources = []
        self.group = group
        self._duration = None
        self._durations = []
        self._counts = []
        self._sourced_candidates = []

    def get_params(self):
        return {
            "sources": [[s.id, n] for s, n in self.sources],
            "group": self.group,
        }

    def get_sourced_candidates(self) -> dict[str]:
        return self._sourced_candidates

    def add(self, source: Source, n: int):
        self.sources.append((source, n))

    def get_durations(self):
        return self._durations

    def get_counts(self):
        return self._counts

    async def _collect_source(self, idx, source: Source, args):
        start_time = time.perf_counter_ns()

        candidates = []

        try:
            candidates = [c for c in source.collect(*args)]
        except Exception as e:
            log_error("Source collection failed", module="feed", error=str(e))

        self._durations[idx] = time.perf_counter_ns() - start_time
        self._counts[idx] = len(candidates)

        for c in candidates:
            self._sourced_candidates[idx].add(c)

        log_debug(
            "Source collected",
            module="feed",
            source=source.id,
            count=len(candidates),
            duration_ms=round(self._durations[idx] / 1_000_000, 2),
        )

        return candidates

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        self._durations = [None for _ in range(len(self.sources))]
        self._counts = [0 for _ in range(len(self.sources))]
        self._sourced_candidates = [set() for _ in range(len(self.sources))]
        jobs = []

        start_time = time.perf_counter_ns()

        for i, (source, n) in enumerate(self.sources):
            jobs.append(self._collect_source(i, source, (n,)))

        results = await asyncio.gather(*jobs)

        self._duration = time.perf_counter_ns() - start_time

        n_sourced = 0
        for batch, (source, _) in zip(results, self.sources):
            for candidate in batch:
                candidates.append(candidate, source=source.id, source_group=self.group)
                n_sourced += 1

        log_debug(
            "Sourcing completed",
            module="feed",
            total_candidates=n_sourced,
            sources=len(self.sources),
            duration_ms=round(self._duration / 1_000_000, 2),
        )

        return candidates


class SamplingStep(PipelineStep):
    def __init__(
        self,
        sampler: Sampler,
        feature_service: Features,
        entity: str,
        n: int = np.inf,
        heuristics: list[Heuristic] = [],
        unique: bool = True,
    ):
        self.seen = set()
        self.n = n
        self.entity = entity
        self.sampler = sampler
        self.heuristics = heuristics
        self.feature_service = feature_service
        self.unique = unique

    def get_params(self):
        return {
            "n": self.n,
            "unique": self.unique,
            "heuristics": [
                {
                    "name": h.id,
                    "params": h.get_params(),
                }
                for h in self.heuristics
            ],
            "sampler": {
                "name": self.sampler.id,
                "params": self.sampler.get_params(),
            },
        }

    def get_state(self):
        return {
            "seen": list(self.seen),
            "heuristics": [h.get_state() for h in self.heuristics],
        }

    def set_state(self, state):
        self.seen = set(state.get("seen", []))
        for heuristic, h_state in zip(self.heuristics, state.get("heuristics")):
            heuristic.set_state(h_state)

    async def _get_adjusted_scores(self, candidates: CandidateList):
        adjusted_candidates = deepcopy(candidates)

        for heuristic in self.heuristics:
            features = None
            if heuristic.features and len(heuristic.features) > 0:
                entity_rows = candidates.get_entity_rows()
                features = await self.feature_service.get(entity_rows, heuristic.features)

            adjusted_candidates._scores = heuristic(adjusted_candidates, features)

        return adjusted_candidates

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        sampled_candidates = CandidateList(candidates.entity)

        if self.unique:
            for seen in self.seen:
                del candidates[seen]

        for _ in range(self.n):
            if len(candidates) == 0:
                break

            while True:
                if len(candidates) == 0:
                    break

                adjusted_scores = await self._get_adjusted_scores(candidates)

                idx = self.sampler.sample(adjusted_scores)

                candidate = candidates[idx]
                candidate.score = adjusted_scores._scores[idx]

                del candidates[candidate.id]

                if self.unique and candidate.id in self.seen:
                    log_debug("Candidate already seen", module="feed", candidate_id=candidate.id)
                    continue

                sampled_candidates.append(candidate)
                self.seen.add(candidate.id)

                for heuristic in self.heuristics:
                    features = (
                        await self.feature_service.get(
                            [{self.entity: candidate.id}], heuristic.features
                        )
                    ).values[0]
                    heuristic.update_seen(candidate, features)

                break

        return sampled_candidates
