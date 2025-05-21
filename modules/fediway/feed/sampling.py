import random

import numpy as np


class Sampler:
    def sample(self, scores) -> int:
        raise NotImplementedError


class TopKSampler(Sampler):
    def sample(self, scores) -> int:
        return np.argsort(scores)[-1]


class InverseTransformSampler(Sampler):
    def sample(self, scores) -> int:
        target = random.uniform(0, np.sum(scores))

        cumulative = 0
        for i, score in enumerate(scores):
            cumulative += score
            if target < cumulative:
                return i

        return len(scores) - 1
