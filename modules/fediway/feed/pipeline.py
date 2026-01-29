import time
from datetime import datetime

import numpy as np

from shared.utils.logging import log_error

from ..heuristics import DiversifyHeuristic, Heuristic
from ..rankers import Ranker
from ..sources import Source
from .candidates import CandidateList
from .features import Features
from .sampling import Sampler, TopKSampler
from .steps import (
    PaginationStep,
    PipelineStep,
    RankingStep,
    RememberStep,
    SamplingStep,
    SourcingStep,
)


class Feed:
    def __init__(self, feature_service: Features):
        self.feature_service = feature_service
        self.steps = []
        self.entity = None
        self._heuristics = []
        self.counter = 0
        self._durations = []
        self._running = False
        self.event_time = datetime.now()

    def get_durations(self) -> list[int]:
        return self._durations

    def is_new(self) -> bool:
        return self.counter == 0

    def get_state(self) -> list[any]:
        return {
            "counter": self.counter,
            "steps": [
                step.get_state() if hasattr(step, "get_state") else None for step in self.steps
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
        async def _step_fn(candidates: CandidateList):
            _, indices = np.unique(candidates.get_candidates(), return_index=True)
            return candidates[indices]

        self.steps.append(_step_fn)

        return self

    def passthrough(self, callback):
        async def _step_fn(candidates: CandidateList):
            await callback(candidates)
            return candidates

        self.steps.append(_step_fn)

        return self

    def with_event_time(self, event_time: datetime):
        self.event_time = event_time

    def remember(self):
        self.steps.append(RememberStep(self.entity))

        return self

    def source(self, source: Source, n: int, group: str | None = None):
        current_step = self.steps[-1] if len(self.steps) > 0 else None

        current_step_is_sourcing_step = self._is_current_step_type(SourcingStep)
        def is_different_group():
            return current_step is not None and current_step.group != group

        if not current_step_is_sourcing_step or is_different_group():
            self.step(SourcingStep(group))

        self.steps[-1].add(source, n)

        return self

    def sources(self, sources: list[tuple[Source, int]], group: str | None = None):
        for source, n in sources:
            self.source(source, n, group)

        return self

    def rank(self, ranker: Ranker, feature_service: Features | None = None):
        self.step(RankingStep(ranker, feature_service or self.feature_service, self.entity))

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
        self.step(PaginationStep(self.entity, int(limit), offset, max_id))

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
            log_error("Pipeline is already running", module="feed")
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

    def results(self, step_idx=None) -> CandidateList:
        step_idx = step_idx or len(self.steps) - 1

        return self.steps[step_idx].results()

    def __getitem__(self, idx):
        return self.steps[idx]
