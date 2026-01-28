import numpy as np

from modules.fediway.feed.sampling import TopKSampler


class DummyCandidateList:
    def __init__(self, scores=[1.0, 3.5, 2.2]):
        self.scores = scores

    def get_scores(self):
        return np.array(self.scores)


def test_topk_sampler_picks_highest_score():
    candidates = DummyCandidateList()
    sampler = TopKSampler()
    assert sampler.sample(candidates) == 1
