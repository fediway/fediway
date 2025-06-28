from loguru import logger
from copy import deepcopy
import pandas as pd
import numpy as np
import asyncio
import time

from ..rankers import Ranker
from ..sources import Source
from ..heuristics import Heuristic, DiversifyHeuristic
from .sampling import TopKSampler, Sampler
from .features import Features


class Candidate:
    def __init__(self, entity, candidate, score, sources):
        self.entity = entity
        self.id = candidate
        self.score = score
        self.sources = sources


class CandidateList:
    def __init__(self, entity: str):
        self.entity = entity
        self._ids = []
        self._scores = []
        self._sources = {}

    def append(
        self,
        candidate,
        score: float = 1.0,
        source: str | list[str] | None = None,
        source_group: str | list[str] | None = None,
    ):
        if type(candidate) == Candidate:
            source = candidate.sources
            score = candidate.score
            candidate = candidate.id

        if source is None:
            sources = set()
        elif type(source) == str:
            sources = set([(source, source_group)])
        else:
            if source_group is None or type(source_group) == str:
                source_group = [source_group for _ in range(len(source))]
            sources = set(zip(source, source_group))

        if candidate in self._sources:
            if source is not None:
                self._sources[candidate] |= sources
        else:
            self._sources[candidate] = sources

        self._ids.append(candidate)
        self._scores.append(score)

    def get_state(self):
        return {
            "ids": self._ids,
            "scores": self._scores,
            "sources": {c: list(s) for c, s in self._sources.items()},
        }

    def set_state(self, state):
        self._ids = state["ids"]
        self._scores = state["scores"]
        self._sources = {c: set(s) for c, s in state["ids"].items()}

    def unique_groups(self) -> set[str]:
        groups = set()
        for sources in self._sources.values():
            for _, group in sources:
                groups.add(group)
        return groups

    def get_entity_rows(self):
        return [{self.entity: c} for c in self._ids]

    def get_scores(self) -> np.ndarray:
        return np.array(self._scores)

    def set_scores(self, scores):
        if type(scores) == np.ndarray:
            self._scores = scores.tolist()
        else:
            self._scores = scores

    def get_candidates(self) -> list:
        return self._ids

    def get_source(self, candidate) -> set[tuple[str, str | None]]:
        return self._sources[candidate]

    def __iadd__(self, other):
        assert type(other) == type(self)

        self._ids += other._ids
        self._scores += other._scores

        for candidate, sources in other._sources.items():
            if candidate not in self._sources:
                self._sources[candidate] = sources
            else:
                self._sources[candidate] |= sources

        return self

    def index(self, candidate):
        return self._ids.index(candidate)

    def __getitem__(self, index):
        if isinstance(index, slice):
            result = CandidateList(self.entity)
            result._ids = self._ids[index]
            result._scores = self._scores[index]
            result._sources = {c: self._sources[c] for c in result._ids}

            return result
        else:
            candidate = self._ids[index]
            score = self._scores[index]
            sources = self._sources[candidate]
            return Candidate(self.entity, candidate, score, sources)

    def __len__(self):
        return len(self._ids)

    def __delitem__(self, candidate):
        try:
            index = self._ids.index(candidate)
            del self._scores[index]
            del self._ids[index]
            del self._sources[candidate]
        except ValueError:
            return


class PipelineStep:
    def results(self) -> tuple[list[int], np.ndarray]:
        raise NotImplementedError

    def get_state(self):
        return None

    def set_state(self, state):
        pass

    async def __call__(
        self, candidates: list[int], scores: np.ndarray
    ) -> tuple[list[int], np.ndarray]:
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

        logger.info(
            f"Ranked {len(candidates)} candidates by {self.ranker.name} in {self._ranking_duration / 1_000_000} ms"
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
            "candidates": self.candidates,
        }

    def set_state(self, state):
        if "candidates" not in self.candidates:
            return
        self.candidates.set_state(state["candidates"])

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        self.candidates += candidates

        return self.candidates


class PaginationStep(PipelineStep):
    def __init__(
        self, entity: str, limit: int, offset: int = 0, max_id: int | None = None
    ):
        self.candidates = CandidateList(entity)
        self.limit = limit
        self.offset = offset
        self.max_id = max_id

    def get_state(self):
        return {"candidates": self.candidates.get_state()}

    def set_state(self, state):
        if not "candidates" in state:
            return
        self.candidates = self.candidates.set_state(state["candidates"])

    def results(self):
        start = 0

        if self.offset is not None:
            start = self.offset
        elif self.max_id is not None:
            try:
                start = self.candidates.index(self.max_id)
            except ValueError:
                return [], np.array([])

        print("start:", start, self.limit)
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
            logger.error(e)

        self._durations[idx] = time.perf_counter_ns() - start_time
        self._counts[idx] = len(candidates)

        # logger.info(f"Collected {len(candidates)} candidates from {source.name()} in {self._durations[idx] / 1_000_000} ms")

        return candidates

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        self._durations = [None for _ in range(len(self.sources))]
        self._counts = [0 for _ in range(len(self.sources))]
        jobs = []

        start_time = time.perf_counter_ns()

        for i, (source, n) in enumerate(self.sources):
            jobs.append(self._collect_source(i, source, (n,)))

        results = await asyncio.gather(*jobs)

        self._duration = time.perf_counter_ns() - start_time

        n_sourced = 0
        for batch, (source, _) in zip(results, self.sources):
            for candidate in batch:
                candidates.append(
                    candidate, source=source.name(), source_group=self.group
                )
                n_sourced += 1

        logger.info(
            f"Collected {n_sourced} candidates from {len(self.sources)} sources in {self._duration / 1_000_000} ms"
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
                features = await self.feature_service.get(
                    entity_rows, heuristic.features
                )

            adjusted_candidates._scores = heuristic(adjusted_candidates, features)

        return adjusted_candidates

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        sampled_candidates = CandidateList(candidates.entity)

        if self.unique:
            for seen in self.seen:
                del candidates[candidate]

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

                del candidates[idx]

                if self.unique and candidate.id in self.seen:
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


class Feed:
    def __init__(self, feature_service: Features):
        self.feature_service = feature_service
        self.steps = []
        self.entity = None
        self._heuristics = []
        self.counter = 0
        self._durations = []
        self._running = False

    def get_durations(self) -> list[int]:
        return self._durations

    def is_new(self) -> bool:
        return self.counter == 0

    def get_state(self) -> list[any]:
        return {
            "counter": self.counter,
            "steps": [
                step.get_state() if hasattr(step, "get_state") else None
                for step in self.steps
            ],
        }

    def set_state(self, state):
        self.counter = state.get("counter", True)
        for step, _state in zip(self.steps, state["steps"]):
            if hasattr(step, "set_state"):
                step.set_state(_state)

    def _is_current_step_type(self, type):
        return len(self.steps) > 0 and isinstance(self.steps[-1], type)

    def step(self, step: PipelineStep):
        self.steps.append(step)

    def select(self, entity: str):
        self.entity = entity

        return self

    def unique(self):
        def _step_fn(candidates, scores):
            candidates, indices = np.unique(candidates, return_index=True)
            return candidates, scores[indices]

        self.steps.append(step_fn)

        return self

    def remember(self):
        self.steps.append(RememberStep(self.entity))

        return self

    def source(self, source: Source, n: int, group: str | None = None):
        current_step = self.steps[-1] if len(self.steps) > 0 else None

        current_step_is_sourcing_step = self._is_current_step_type(SourcingStep)
        is_different_group = (
            lambda: current_step is not None and current_step.group != group
        )

        if not current_step_is_sourcing_step or is_different_group():
            self.step(SourcingStep(group))

        self.steps[-1].add(source, n)

        return self

    def sources(self, sources: list[tuple[Source, int]], group: str | None = None):
        for source, n in sources:
            self.source(source, n, group)

        return self

    def rank(self, ranker: Ranker, feature_service: Features | None = None):
        self.step(
            RankingStep(ranker, feature_service or self.feature_service, self.entity)
        )

        return self

    def sample(self, n: int, sampler: Sampler = TopKSampler(), unique=True):
        self.step(
            SamplingStep(
                sampler,
                feature_service=self.feature_service,
                entity=self.entity,
                heuristics=self._heuristics,
                unique=unique,
                n=n,
            )
        )
        self._heuristics = []

        return self

    def paginate(self, limit: int, offset: int = 0, max_id: int | None = None):
        self.step(PaginationStep(int(limit), offset, max_id))

        return self

    def heuristic(self, heuristic: Heuristic):
        self._heuristics.append(heuristic)

        return self

    def diversify(self, by, penalty: float = 0.1):
        return self._heuristics.append(DiversifyHeuristic(by, penalty))

        return self

    async def _execute_step(self, idx, candidates: CandidateList) -> CandidateList:
        # # filter seen
        # remove_indices = []
        # for candidate in candidates:
        #     self.seen[idx].add(candidate)

        # # add seen
        # for candidate in candidates:
        #     self.seen[idx].add(candidate)

        candidates = await self.steps[idx](candidates)

        # for candidate, score in zip(candidates, scores):
        #     self.cache[i][candidate] = score

        return candidates

    async def execute(self) -> list[int]:
        if self._running:
            logger.error("Pipeline is already running.")
            return

        self._running = True
        candidates = CandidateList(self.entity)

        self._durations = []

        for i in range(len(self.steps)):
            start_time = time.perf_counter_ns()

            candidates = await self._execute_step(i, candidates)

            self._durations.append(time.perf_counter_ns() - start_time)

        self.counter += 1
        self._running = False

        return self

    def results(self, step_idx=None):
        step_idx = step_idx or len(self.steps) - 1

        return self.steps[step_idx].results()

    def __getitem__(self, idx):
        return self.steps[idx]
