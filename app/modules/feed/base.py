
import numpy as np
from enum import Enum

from ..heuristics import Heuristic
from .candidate import Candidate
from .utils import TopKPriorityQueue

class SamplingStrategy(Enum):
    TOPK = 'topk'

    def sample(self, scores: list[float]) -> int:
        if self == SamplingStrategy.TOPK:
            return np.argsort(scores)[-1]

        raise NotImplemented

class Feed():
    user: None = None
    seen_ids = set()
    candidate_queues: dict[str, TopKPriorityQueue] = {}
    heuristics: list[Heuristic] = []

    def __init__(self, 
                 id: int,
                 name: str,
                 max_queue_size: int,
                 heuristics: list[Heuristic] = []):
        self.id = id
        self.name = name
        self.max_queue_size = max_queue_size
        self.heuristics = heuristics

    def add_candidates(self, queue: str, candidates: list[Candidate]):
        if not queue in self.candidate_queues:
            self.candidate_queues[queue] = TopKPriorityQueue(self.max_queue_size)

        for candidate in candidates:

            # cannot insert candidates that have been added to the feed
            if candidate.status_id in self.seen_ids:
                continue

            self.candidate_queues[queue].add(candidate, candidate.score)

    def reset(self, queue: str):
        self.candidate_queues[queue].reset()

    def is_empty(self):
        return len(self.candidate_queues) == 0

    def get_adjusted_scores(self, queue_name: str):
        '''
        Gets scores adjusted by heuristics for a queue.
        '''
        candidates = self.candidate_queues[queue_name].items()
        scores = np.array(self.candidate_queues[queue_name].scores().copy())
        
        for heuristic in self.heuristics:
            scores = heuristic(candidates, scores)
        
        return scores

    def samples(self, 
                queue_name: str, 
                n: int, 
                strategy: SamplingStrategy = SamplingStrategy.TOPK):

        samples = []

        for i in range(n):
            while True:
                adjusted_scores = self.get_adjusted_scores(queue_name)

                if len(adjusted_scores) == 0:
                    break

                idx = strategy.sample(adjusted_scores)
                candidate = self.candidate_queues[queue_name][idx][-1]

                del self.candidate_queues[queue_name].heap[idx]
                
                if candidate.status_id in self.seen_ids:
                    continue

                self.seen_ids.add(candidate.status_id)
                samples.append((candidate, adjusted_scores[idx]))

                for heuristic in self.heuristics:
                    heuristic.update(candidate)

                break

        return samples