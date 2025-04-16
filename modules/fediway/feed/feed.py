
import threading
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

        self._sourced_candidates = []
        self._sourced_candidates_condition = threading.Condition()
        self._ranker_condition = threading.Condition()
        self._active_sources = []
        self._active_sources_lock = threading.Lock()

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

    def push(self, candidate, source_name: str):
        with self._sourced_candidates_condition:
            if candidate in self.candidate_sources:
                return
            
            self._sourced_candidates.append(candidate)
            self.candidate_sources[str(candidate)] = []
            self.candidate_sources[str(candidate)].append(source_name)
            self._sourced_candidates_condition.notify_all()

    def collect_async(self, source, args, rank_after_completion: bool = True, callback=None):
        """Asynchronously collect candidates from a source using a background thread.
        
        Launches a daemon thread to consume items from the source's collect() generator
        and push them to the shared candidate storage. 
        
        Args:
            source: Object implementing collect() generator method
            args: Arguments to pass to source.collect() method
            rank_after_completion: Whether the collected candidates should be ranked.
        """

        def _consume_source(source, source_args, rank_after_completion):
            n = 0
            for candidate in source.collect(*source_args):
                if candidate in self.seen_candidates:
                    continue
                self.push(candidate, str(source))
                n += 1
            if callback is not None:
                callback(n)
            if rank_after_completion:
                self._handle_source_completion()

        thread = threading.Thread(
            target=_consume_source, 
            args=(source, args, rank_after_completion)
        )
        thread.daemon = True
        with self._active_sources_lock:
            self._active_sources.append(thread)
        thread.start()

    def _handle_source_completion(self):
        with self._active_sources_lock:
            if any(t.is_alive() for t in self._active_sources):
                return

            # Clean up finished threads
            self._active_sources = [t for t in self._active_sources if t.is_alive()]

            # All threads completed if list is empty after cleanup
            if not self._active_threads and self.completion_callback:
                candidates = self._sourced_candidates
                self._sourced_candidates = []

                # Launch ranking of collected sources
                self.rank_async(candidates, ranker_index=0)

    def rank_async(self, candidates: list[int | str] | None = None, ranker_index: int = 0):
        if ranker_index >= len(self.rankers):
            return

        def _rank(candidates, idx):
            ranker = self.rankers[idx]
            queue = self.candidate_queues[idx]
            X = self.features.get(candidates, ranker.features)
            scores = ranker.predict(X)

            with self._ranker_condition:
                # reset queue if it is not the final candidate queue
                if idx != len(self.rankers) - 1:
                    queue.reset()

                for candidate, score in zip(candidates, scores):
                    queue.add(candidate, score)

                with self._ranker_condition:
                    self._ranker_condition.notify_all()

            if idx+1 >= len(self.rankers):
                return

            next_candidates = [item for item, _ in queue.get_unsorted_items()]
            self.rank_async(next_candidates, idx + 1)

        if candidates is None and ranker_index == 0:
            with self._active_sources_lock:
                candidates = self._sourced_candidates
                self._sourced_candidates = []
        else:
            raise ValueError("Candidates missing.")
        
        thread = threading.Thread(target=_rank, args=(candidates, ranker_index))
        thread.daemon = True
        with self._active_sources_lock:
            self._active_sources.append(thread)
        thread.start()

    def wait_for_candidates(self, n: int, max_t: timedelta = timedelta(seconds=5)) -> bool:
        """Block until specified number of candidates are collected or timeout occurs.
        
        Args:
            n: Minimum number of candidates to wait for
            max_t: Maximum time to wait
        
        Returns:
            bool: True if at least n candidates were collected, False if timed out
        """

        end_time = time.monotonic() + max_t.total_seconds()
        with self._sourced_candidates_condition:
            while len(self._sourced_candidates) < n:
                remaining = end_time - time.monotonic()
                if remaining <= 0:
                    break
                self._sourced_candidates_condition.wait(remaining)
            return len(self._sourced_candidates) >= n

    def wait_for_ranker(self, ranker_index: int = 0, max_t: timedelta = timedelta(seconds=1)) -> bool:
        """Block until specified number of candidates are collected or timeout occurs.
        
        Args:
            n: Minimum number of candidates to wait for
            max_t: Maximum time to wait (default: 1 second)
        
        Returns:
            bool: True if at least n candidates were collected, False if timed out
        """

        end_time = time.monotonic() + max_t.total_seconds()
        with self._ranker_condition:
            while True:
                for queue in reversed(self.candidate_queues[ranker_index:]):
                    if len(queue) > 0:
                        return True

                remaining = end_time - time.monotonic()
                if remaining <= 0:
                    return False
            
                self._ranker_condition.wait(remaining)

    def iter_batch(self, batch_size: int):
        return BatchIterator(self, batch_size)

    def get_batch(self, batch_size) -> list[Recommendation]:
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
            if len(queue) > 0:
                return idx

    def __next__(self) -> Recommendation | None:
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