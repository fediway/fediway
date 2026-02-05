import random
from typing import ClassVar

import numpy as np

from shared.utils.strings import camel_to_snake, humanize


class Sampler:
    _id: ClassVar[str | None] = None
    _display_name: ClassVar[str | None] = None
    _description: ClassVar[str | None] = None
    _tracked_params: ClassVar[list[str]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "_tracked_params" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must define _tracked_params. "
                f"Use empty list [] if no params to track."
            )

    @property
    def id(self) -> str:
        if self._id:
            return self._id
        return camel_to_snake(self.__class__.__name__)

    @property
    def display_name(self) -> str:
        if self._display_name:
            return self._display_name
        name = self.__class__.__name__
        for suffix in ("Sampler",):
            name = name.removesuffix(suffix)
        return humanize(camel_to_snake(name))

    @property
    def description(self) -> str | None:
        if self._description:
            return self._description
        if self.__doc__:
            return self.__doc__.strip().split("\n")[0]
        return None

    @property
    def class_path(self) -> str:
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    def get_params(self) -> dict:
        return {k: getattr(self, k) for k in self._tracked_params}

    def sample(self, candidates) -> int:
        raise NotImplementedError


class TopKSampler(Sampler):
    _tracked_params = []

    def sample(self, candidates) -> int:
        return np.argsort(candidates.get_scores())[-1]


class InverseTransformSampler(Sampler):
    _tracked_params = []

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
    _tracked_params = ["weights"]

    def __init__(self, weights: dict[str, float]):
        self.weights = weights

    def sample(self, candidates) -> int:
        if len(candidates) == 0:
            return

        groups = [g for g in candidates.unique_groups() if g in self.weights]
        random.shuffle(groups)
        weights = [self.weights[g] for g in groups]

        if len(groups) == 0:
            raise ValueError("No matching groups found in candidates for configured weights")

        probs = np.array(weights) / sum(weights)
        target_group = np.random.choice(groups, p=probs)

        indices = []
        scores = []

        for i, c in enumerate(candidates.get_candidates()):
            for source, g in candidates.get_source(c):
                if target_group == g:
                    indices.append(i)
                    scores.append(candidates._scores[i])

        perm = np.random.permutation(len(indices))

        indices = np.array(indices)[perm]
        scores = np.array(scores)[perm]

        if sum(scores):
            p = np.array(scores) / sum(scores)
        else:
            p = np.ones(len(scores)) / len(scores)

        return np.random.choice(indices, p=p)
