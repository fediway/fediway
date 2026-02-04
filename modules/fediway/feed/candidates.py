import numpy as np


class Candidate:
    def __init__(
        self,
        entity: str,
        candidate: int,
        score: float | None,
        sources: set[tuple[str, str]],
    ):
        self.entity = entity
        self.id = candidate
        self.score = score
        self.sources = sources


class CandidateList:
    def __init__(self, entity: str):
        self.entity = entity
        self._ids = []
        self._scores = []
        self._sources = {}

    def append(
        self,
        candidate,
        score: float = 1.0,
        source: str | list[str] | None = None,
        source_group: str | list[str] | None = None,
    ):
        if isinstance(candidate, Candidate):
            source = [s for s, _ in candidate.sources]
            source_group = [g for _, g in candidate.sources]
            score = candidate.score
            candidate = candidate.id

        if source is None:
            sources = set()
        elif isinstance(source, str):
            sources = set([(source, source_group)])
        else:
            if source_group is None or isinstance(source_group, str):
                source_group = [source_group for _ in range(len(source))]
            sources = set(zip(source, source_group))

        if candidate in self._sources:
            if source is not None:
                self._sources[candidate] |= sources
        else:
            self._sources[candidate] = sources

        self._ids.append(candidate)
        self._scores.append(score)

    def get_state(self):
        return {
            "ids": self._ids,
            "scores": self._scores,
            "sources": {c: list(s) for c, s in self._sources.items()},
        }

    def set_state(self, state):
        dtype = int
        if len(state["ids"]) > 0 and isinstance(state["ids"][0], str):
            dtype = str

        self._ids = state["ids"]
        self._scores = state["scores"]
        self._sources = {
            dtype(c): set([(s, g) for s, g in sources]) for c, sources in state["sources"].items()
        }

    def unique_groups(self) -> set[str]:
        groups = set()
        for sources in self._sources.values():
            for _, group in sources:
                groups.add(group)
        return groups

    def get_entity_rows(self):
        return [{self.entity: c} for c in self._ids]

    def get_scores(self) -> np.ndarray:
        return np.array(self._scores)

    def set_scores(self, scores):
        if isinstance(scores, np.ndarray):
            self._scores = scores.tolist()
        else:
            self._scores = scores

    def get_candidates(self) -> list:
        return self._ids

    def get_source(self, candidate) -> set[tuple[str, str | None]]:
        if candidate in self._sources:
            return self._sources[candidate]
        return set()

    def __iadd__(self, other):
        assert isinstance(other, CandidateList)

        self._ids += other._ids
        self._scores += other._scores

        for candidate, sources in other._sources.items():
            if candidate not in self._sources:
                self._sources[candidate] = sources
            else:
                self._sources[candidate] |= sources

        return self

    def index(self, candidate):
        return self._ids.index(candidate)

    def __getitem__(self, index):
        if isinstance(index, slice):
            result = CandidateList(self.entity)
            result._ids = self._ids[index]
            result._scores = self._scores[index]
            result._sources = {c: self._sources.get(c) or set() for c in result._ids}

            return result

        elif isinstance(index, np.ndarray):
            if index.dtype == bool:
                # Boolean mask indexing
                result = CandidateList(self.entity)
                result._ids = [i for i, flag in zip(self._ids, index) if flag]
                result._scores = [s for s, flag in zip(self._scores, index) if flag]
                result._sources = {c: self._sources.get(c) or set() for c in result._ids}
                return result
            else:
                # Index array
                result = CandidateList(self.entity)
                result._ids = [self._ids[i] for i in index]
                result._scores = [self._scores[i] for i in index]
                result._sources = {c: self._sources.get(c) or set() for c in result._ids}
                return result

        else:
            candidate = self._ids[index]
            score = self._scores[index]
            sources = self._sources.get(candidate, set())
            return Candidate(self.entity, candidate, score, sources)

    def __len__(self):
        return len(self._ids)

    def __delitem__(self, candidate):
        try:
            index = self._ids.index(candidate)
            del self._scores[index]
            del self._ids[index]
            del self._sources[candidate]
        except ValueError:
            return

    def __iter__(self):
        return CandidateListIterator(self)


class CandidateListIterator:
    def __init__(self, candidates: CandidateList):
        self.candidates = candidates
        self.index = 0

    def __next__(self) -> Candidate:
        if self.index < len(self.candidates):
            c = self.candidates[self.index]
            self.index += 1
            return c
        else:
            raise StopIteration
