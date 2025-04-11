
import numpy as np

class Sampler():
    def sample(self, scores) -> int:
        raise NotImplementedError

class TopKSampler(Sampler):
    def sample(self, scores) -> int:
        return np.argsort(scores)[-1]