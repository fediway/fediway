import random

import numpy as np


class Sampler:
    def sample(self, candidates) -> int:
        raise NotImplementedError


class TopKSampler(Sampler):
    def sample(self, candidates) -> int:
        return np.argsort(scores)[-1]


class InverseTransformSampler(Sampler):
    def sample(self, candidates) -> int:
        scores = candidates.get_scores()

        target = random.uniform(0, np.sum(scores))

        cumulative = 0
        for i, score in enumerate(scores):
            cumulative += score
            if target < cumulative:
                return i

        return len(scores) - 1


class WeightedGroupSampler(Sampler):
    def __init__(self, weights: dict[str, float]):
        self.weights = weights

    def sample(self, candidates) -> int:
        if len(candidates) == 0:
            return

        groups = [g for g in candidates.unique_groups() if g in self.weights]
        weights = [self.weights[g] for g in groups]

        assert len(groups) > 0

        probs = np.array(weights) / sum(weights)
        target_group = np.random.choice(groups, p=probs)

        indices = []
        scores = []
        for i, c in enumerate(candidates.get_candidates()):
            for source, g in candidates.get_source(c):
                if target_group == g:
                    indices.append(i)
                    scores.append(candidates._scores[i])

        if sum(scores):
            p = np.array(scores) / sum(scores)
        else:
            p = np.ones(len(scores)) / len(scores)

        return np.random.choice(indices, p=p)
