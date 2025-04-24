
import asyncio
from datetime import timedelta
import numpy as np
import time

from ..rankers import Ranker
from .heuristics import Heuristic
from .sampling import Sampler, TopKSampler
from .features import Features
from .utils import BatchIterator, TopKPriorityQueue

class Recommendation:
    item: str | int
    score: float
    adjusted_score: float
    sources: list[str]

    def __init__(self, item: str | int, score: float, adjusted_score: float, sources: list[str]):
        self.item = item
        self.score = float(score)
        self.adjusted_score = float(adjusted_score)
        self.sources = sources

class Feed():
    seen_candidates: set[str | int]
    rankers: list[tuple[Ranker, int]]
    features: Features
    heuristics: list[Heuristic]
    candidate_queues: dict[str, TopKPriorityQueue]
    candidate_sources: dict[str | int, list[str]]
    sampler = Sampler

    def __init__(self, 
                 rankers: list[tuple[Ranker, int]], 
                 features: Features,
                 heuristics: list[Heuristic] = [],
                 sampler: Sampler = TopKSampler()):
        self.rankers = [r for r, _ in rankers]
        self.features = features
        self.heuristics = heuristics
        self.sampler = sampler
        self.candidate_queues = [TopKPriorityQueue(k) for r, k in rankers]
        self.seen_candidates = set()
        self.candidate_sources = {}

        self._sourced_candidates = set()
        self._sourced_candidates_condition = asyncio.Condition()
        self._active_sources = []

    def __len__(self) -> int:
        return sum([len(q) for q in self.candidate_queues])

    def merge_dict(self, data):
        self.id = data['id']
        self.heuristics = [h.from_dict(data) for h, data in zip(self.heuristics, data['heuristics'])]
        self.seen_candidates = set(data['seen_candidates'])
        self.candidate_queues = [TopKPriorityQueue.from_dict(q) for q in data['candidate_queues']]
        self.candidate_sources = data['candidate_sources']

    def to_dict(self):
        return {
            'id': self.id,
            'heuristics': [h.to_dict() for h in self.heuristics],
            'seen_candidates': list(self.seen_candidates),
            'candidate_queues': [q.to_dict() for q in self.candidate_queues],
            'candidate_sources': self.candidate_sources,
        }

    async def push(self, candidate, source_name: str):
        async with self._sourced_candidates_condition:
            if candidate in self._sourced_candidates:
                return
            
            self._sourced_candidates.add(candidate)
            self.candidate_sources[str(candidate)] = []
            self.candidate_sources[str(candidate)].append(source_name)
            self._sourced_candidates_condition.notify_all()

    async def collect(self, source, args) -> int:
        n = 0
        for candidate in source.collect(*args):
            if candidate in self.seen_candidates:
                continue
            await self.push(candidate, str(source))
            n += 1

        return n

    async def rank(self, candidates: list[int | str] | None = None, ranker_index: int = 0):
        if ranker_index >= len(self.rankers):
            return

        if candidates is None and ranker_index == 0:
            async with self._sourced_candidates_condition:
                candidates = self._sourced_candidates
                self._sourced_candidates = set()
        else:
            raise ValueError("Candidates missing.")

        ranker = self.rankers[ranker_index]
        queue = self.candidate_queues[ranker_index]

        X = self.features.get(candidates, ranker.features)
        scores = ranker.predict(X)
        
        # reset queue if it is not the final candidate queue
        if ranker_index != len(self.rankers) - 1:
            queue.reset()

        for candidate, score in zip(candidates, scores):
            queue.add(candidate, score)

        if ranker_index + 1 >= len(self.rankers):
            return

        next_candidates = [item for item, _ in queue.get_unsorted_items()]
        await self.rank(next_candidates, ranker_index + 1)
    
    def iter_batch(self, batch_size: int):
        return BatchIterator(self, batch_size)

    def get_batch(self, batch_size) -> list[Recommendation]:
        print("foo")
        return [item for item in self.iter_batch(batch_size)]

    def _get_adjusted_scores(self, queue_idx):
        '''
        Gets scores adjusted by heuristics for a queue.
        '''

        candidates = self.candidate_queues[queue_idx].items()
        scores = np.array(self.candidate_queues[queue_idx].scores().copy())
        adjusted_scores = scores.copy()
        
        for heuristic in self.heuristics:
            adjusted_scores = heuristic(
                candidates, 
                adjusted_scores, 
                self.features.get(candidates, heuristic.features)
            )
        
        return scores, adjusted_scores
    
    def _get_queue_idx(self):
        for idx, queue in enumerate(reversed(self.candidate_queues)):
            print(idx, queue, len(queue))
            if len(queue) > 0:
                return idx

    def __next__(self) -> Recommendation | None:
        print("hello")
        queue_idx = self._get_queue_idx()

        if queue_idx is None:
            raise StopIteration

        while True:
            scores, adjusted_scores = self._get_adjusted_scores(queue_idx)

            if len(adjusted_scores) == 0:
                raise StopIteration

            idx = self.sampler.sample(adjusted_scores)
            candidate = self.candidate_queues[queue_idx][idx][-1]

            del self.candidate_queues[queue_idx].heap[idx]
            
            if candidate in self.seen_candidates:
                continue

            self.seen_candidates.add(candidate)
            
            for heuristic in self.heuristics:
                heuristic.update_seen(
                    candidate, 
                    self.features.get([candidate], heuristic.features)[0]
                )

            return Recommendation(
                item=candidate,
                score=scores[idx],
                adjusted_score=adjusted_scores[idx],
                sources=self.candidate_sources[str(candidate)]
            )