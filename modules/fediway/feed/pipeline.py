import numpy as np
import asyncio

from ..rankers import Ranker
from ..sources import Source
from ..heuristics import Heuristic, DiversifyHeuristic
from .sampling import TopKSampler, Sampler
from .features import Features


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

    async def __call__(
        self, candidates: list[int], scores: np.ndarray
    ) -> tuple[list[int], np.ndarray]:
        if len(candidates) == 0:
            return candidates, scores

        entities = [{self.entity: c} for c in candidates]
        X = self.feature_service.get(entities, self.ranker.features)

        return candidates, self.ranker.predict(X)


class RememberStep(PipelineStep):
    items: list[int] = []
    scores: list[float] = []

    def get_state(self):
        return {
            "items": self.items,
            "scores": self.scores,
        }

    def set_state(self, state):
        self.items = state.get("items", [])
        self.scores = state.get("scores", [])

    async def __call__(
        self, candidates: list[int], scores: np.ndarray
    ) -> tuple[list[int], np.ndarray]:
        self.items = candidates + self.items
        self.scores = scores.tolist() + self.scores

        return self.items, np.array(self.scores, dtype=np.float32)


class PaginationStep(PipelineStep):
    items: list[int] = []
    scores: list[float] = []

    def __init__(self, limit: int, offset: int = 0):
        self.limit = limit
        self.offset = offset

    def get_state(self):
        return {
            "items": self.items,
            "scores": self.scores,
        }

    def set_state(self, state):
        self.items = state.get("items", [])
        self.scores = state.get("scores", [])

    def results(self):
        start, end = self.offset, self.offset + self.limit

        print(len(self.items), len(np.unique(self.items)))

        return (self.items[start:end], np.array(self.scores[start:end]))

    def __len__(self) -> int:
        return len(self.items)

    async def __call__(
        self, candidates: list[int], scores: np.ndarray
    ) -> tuple[list[int], np.ndarray]:
        self.items += candidates
        self.scores += scores.tolist()

        return self.results()


class SourcingStep(PipelineStep):
    collected = set()

    def __init__(self, sources: list[(Source, int)] = []):
        self.sources = sources

    def add(self, source: Source, n: int):
        self.sources.append((source, n))

    async def _collect_source(self, source: Source, args):
        return [c for c in source.collect(*args)]

    async def __call__(
        self, candidates: list[int], scores: np.ndarray
    ) -> tuple[list[int], np.ndarray]:
        jobs = []

        for source, n in self.sources:
            jobs.append(self._collect_source(source, (n,)))

        results = await asyncio.gather(*jobs)

        n_new = 0
        for new_candidates in results:
            candidates += new_candidates
            n_new += len(new_candidates)

        scores = np.concatenate([scores, np.zeros(n_new)])

        return candidates, scores


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

    def _get_adjusted_scores(self, candidates, scores):
        adjusted_scores = scores.copy()

        for heuristic in self.heuristics:
            features = None
            if heuristic.features and len(heuristic.features) > 0:
                entities = [{self.entity: c} for c in candidates]
                features = self.feature_service.get(entities, heuristic.features)

            adjusted_scores = heuristic(candidates, adjusted_scores, features)

        return adjusted_scores

    async def __call__(
        self, candidates: list[int], scores: np.ndarray
    ) -> tuple[list[int], np.ndarray]:
        sampled_candidates = []
        sampled_scores = []

        if self.unique:
            scores = scores[[i for i, c in enumerate(candidates) if c not in self.seen]]
            candidates = [c for c in candidates if c not in self.seen]

        for _ in range(self.n):
            if len(candidates) == 0:
                break

            while True:
                if len(candidates) == 0:
                    break

                adjusted_scores = self._get_adjusted_scores(candidates, scores)

                idx = self.sampler.sample(adjusted_scores)

                candidate = candidates[idx]
                score = adjusted_scores[idx]

                del candidates[idx]
                scores = np.delete(scores, idx)

                if self.unique and candidate in self.seen:
                    continue

                sampled_candidates.append(candidate)
                sampled_scores.append(score)
                self.seen.add(candidate)

                for heuristic in self.heuristics:
                    features = self.feature_service.get(
                        [{self.entity: candidate}], heuristic.features
                    )[0]
                    heuristic.update_seen(candidate, features)

                break

        return sampled_candidates, np.array(sampled_scores)


class Feed:
    pipeline: list[PipelineStep] = []
    entity: str

    def __init__(self, feature_service: Features):
        self.feature_service = feature_service
        self.pipeline = []
        self._heuristics = []
        self._is_new = True

    def is_new(self) -> bool:
        return self._is_new

    def get_state(self) -> list[any]:
        return {
            "is_new": self._is_new,
            "pipeline": [
                step.get_state() if hasattr(step, "get_state") else None
                for step in self.pipeline
            ],
        }

    def set_state(self, state):
        self._is_new = state.get("is_new", True)
        for step, _state in zip(self.pipeline, state["pipeline"]):
            if hasattr(step, "set_state"):
                step.set_state(_state)

    def _is_current_step_type(self, type):
        return len(self.pipeline) > 0 and isinstace(self.pipeline[-1], type)

    def step(self, step: PipelineStep):
        self.pipeline.append(step)

    def select(self, entity: str):
        self.entity = entity

        return self

    def unique(self):
        def _step_fn(candidates, scores):
            candidates, indices = np.unique(candidates, return_index=True)
            return candidates, scores[indices]

        self.pipeline.append(step_fn)

        return self

    def remember(self):
        self.pipeline.append(RememberStep())

        return self

    def source(self, source: Source, n: int):
        if not self._is_current_step_type(SourcingStep):
            self.step(SourcingStep())
        self.pipeline[-1].add(source, n)

        return self

    def sources(self, sources: list[tuple[Source, int]]):
        if not self._is_current_step_type(SourcingStep):
            self.step(SourcingStep())
        for source, n in sources:
            self.pipeline[-1].add(source, n)

        return self

    def rank(self, ranker: Ranker):
        self.step(RankingStep(ranker, self.feature_service, self.entity))

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

    def paginate(self, limit: int, offset: int = 0):
        self.step(PaginationStep(limit, offset))

        return self

    def heuristic(self, heuristic: Heuristic):
        self._heuristics.append(heuristic)

        return self

    def diversify(self, by, penalty: float = 0.1):
        return self._heuristics.append(DiversifyHeuristic(by, penalty))

        return self

    async def _execute_step(
        self, idx, candidates: list[int], scores: np.ndarray
    ) -> tuple[list[int], np.ndarray]:
        # # filter seen
        # remove_indices = []
        # for candidate in candidates:
        #     self.seen[idx].add(candidate)

        # # add seen
        # for candidate in candidates:
        #     self.seen[idx].add(candidate)

        candidates, scores = await self.pipeline[idx](candidates, scores)

        # for candidate, score in zip(candidates, scores):
        #     self.cache[i][candidate] = score

        return candidates, scores

    async def execute(self) -> list[int]:
        candidates = []
        scores = np.array([], dtype=np.float32)

        for i in range(len(self.pipeline)):
            candidates, scores = await self._execute_step(i, candidates, scores)

        self._is_new = False

        return self

    def results(self, step_idx=None):
        step_idx = step_idx or len(self.pipeline) - 1

        candidates, _ = self.pipeline[step_idx].results()

        return candidates

    def __getitem__(self, idx):
        return self.pipeline[idx]
