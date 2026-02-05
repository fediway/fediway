import numpy as np


class Candidate:
    def __init__(
        self,
        entity: str,
        candidate: int,
        score: float | np.ndarray | None,
        sources: set[tuple[str, str]],
    ):
        self.entity = entity
        self.id = candidate
        self.score = score
        self.sources = sources


class CandidateList:
    def __init__(self, entity: str | list[str] | None = None):
        # Normalize entity to list for uniform handling
        if entity is None:
            self._entity_types = []
            self.entity = None
        elif isinstance(entity, str):
            self._entity_types = [entity]
            self.entity = entity
        else:
            self._entity_types = list(entity)
            self.entity = self._entity_types[0] if self._entity_types else None

        self._ids = []
        self._entities = []  # Per-position entity type
        self._scores = None  # np.ndarray, shape (N,) for scalars or (N, D) for vectors
        self._sources = {}

    @property
    def entity_types(self) -> list[str]:
        """List of entity types this CandidateList can hold."""
        return self._entity_types

    def append(
        self,
        candidate,
        score: float | np.ndarray = 1.0,
        source: str | list[str] | None = None,
        source_group: str | list[str] | None = None,
        entity: str | None = None,
    ):
        if isinstance(candidate, Candidate):
            source = [s for s, _ in candidate.sources]
            source_group = [g for _, g in candidate.sources]
            score = candidate.score
            entity = candidate.entity
            candidate = candidate.id

        # Determine entity type for this candidate
        if entity is None:
            entity = self.entity  # Use primary entity
        elif self._entity_types and entity not in self._entity_types:
            raise ValueError(f"Entity type '{entity}' not in allowed types: {self._entity_types}")

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
        self._entities.append(entity)

        # Handle score appending
        score_arr = np.atleast_1d(np.asarray(score))
        if self._scores is None:
            # First score determines shape
            if score_arr.ndim == 0 or (score_arr.ndim == 1 and score_arr.shape[0] == 1):
                self._scores = np.array([float(score)])
            else:
                self._scores = score_arr.reshape(1, -1)
        else:
            if self._scores.ndim == 1:
                # Scalar scores
                self._scores = np.append(
                    self._scores, float(score) if np.isscalar(score) else score_arr[0]
                )
            else:
                # Vector scores
                self._scores = np.vstack([self._scores, score_arr.reshape(1, -1)])

    def get_state(self):
        state = {
            "ids": self._ids,
            "entities": self._entities,
            "scores": self._scores.tolist() if self._scores is not None else [],
            "sources": {c: list(s) for c, s in self._sources.items()},
        }
        return state

    def set_state(self, state):
        dtype = int
        if len(state["ids"]) > 0 and isinstance(state["ids"][0], str):
            dtype = str

        self._ids = state["ids"]
        self._scores = np.array(state["scores"]) if state["scores"] else None
        self._sources = {
            dtype(c): set([(s, g) for s, g in sources]) for c, sources in state["sources"].items()
        }

        # Restore entities (backwards compat: default to primary entity)
        if "entities" in state:
            self._entities = state["entities"]
        else:
            self._entities = [self.entity] * len(self._ids)

    def unique_groups(self) -> set[str]:
        groups = set()
        for sources in self._sources.values():
            for _, group in sources:
                groups.add(group)
        return groups

    def get_entity_rows(self):
        """Return entity rows for feature service, using per-candidate entity type."""
        if not self._entities:
            return [{self.entity: c} for c in self._ids]
        return [{self._entities[i]: self._ids[i]} for i in range(len(self._ids))]

    def get_scores(self) -> np.ndarray:
        """Get scores array. Shape is (N,) for scalars or (N, D) for vectors."""
        if self._scores is None:
            return np.array([])
        return self._scores

    def set_scores(self, scores):
        """Set scores array. Can be 1D (scalars) or 2D (vectors)."""
        self._scores = np.asarray(scores)

    def get_candidates(self) -> list:
        return self._ids

    def get_source(self, candidate) -> set[tuple[str, str | None]]:
        if candidate in self._sources:
            return self._sources[candidate]
        return set()

    def __iadd__(self, other):
        if not isinstance(other, CandidateList):
            raise TypeError(f"Cannot add {type(other).__name__} to CandidateList")

        self._ids += other._ids
        self._entities += other._entities if other._entities else [other.entity] * len(other._ids)

        # Merge scores
        if other._scores is not None:
            if self._scores is None:
                self._scores = other._scores.copy()
            else:
                self._scores = np.concatenate([self._scores, other._scores])

        for candidate, sources in other._sources.items():
            if candidate not in self._sources:
                self._sources[candidate] = sources
            else:
                self._sources[candidate] |= sources

        return self

    def index(self, candidate):
        return self._ids.index(candidate)

    def _get_score_at(self, index: int):
        """Get score at index, returns scalar or vector depending on scores shape."""
        if self._scores is None:
            return None
        if self._scores.ndim == 1:
            return float(self._scores[index])
        return self._scores[index]

    def __getitem__(self, index):
        if isinstance(index, slice):
            result = CandidateList(self._entity_types if self._entity_types else self.entity)
            result._ids = self._ids[index]
            result._entities = self._entities[index] if self._entities else []
            result._scores = self._scores[index] if self._scores is not None else None
            result._sources = {c: self._sources.get(c) or set() for c in result._ids}
            return result

        elif isinstance(index, np.ndarray):
            if index.dtype == bool:
                # Boolean mask indexing
                result = CandidateList(self._entity_types if self._entity_types else self.entity)
                result._ids = [i for i, flag in zip(self._ids, index) if flag]
                result._entities = (
                    [e for e, flag in zip(self._entities, index) if flag] if self._entities else []
                )
                result._scores = self._scores[index] if self._scores is not None else None
                result._sources = {c: self._sources.get(c) or set() for c in result._ids}
                return result
            else:
                # Index array
                result = CandidateList(self._entity_types if self._entity_types else self.entity)
                result._ids = [self._ids[i] for i in index]
                result._entities = [self._entities[i] for i in index] if self._entities else []
                result._scores = self._scores[index] if self._scores is not None else None
                result._sources = {c: self._sources.get(c) or set() for c in result._ids}
                return result

        else:
            candidate = self._ids[index]
            score = self._get_score_at(index)
            entity = self._entities[index] if self._entities else self.entity
            sources = self._sources.get(candidate, set())
            return Candidate(entity, candidate, score, sources)

    def __len__(self):
        return len(self._ids)

    def __delitem__(self, candidate):
        try:
            index = self._ids.index(candidate)
            if self._scores is not None:
                self._scores = np.delete(self._scores, index, axis=0)
            del self._ids[index]
            if self._entities:
                del self._entities[index]
            del self._sources[candidate]
        except ValueError:
            return

    def __iter__(self):
        return CandidateListIterator(self)

    def copy(self) -> "CandidateList":
        """Create a shallow copy of this list."""
        new = CandidateList(self._entity_types if self._entity_types else self.entity)
        new._ids = list(self._ids)
        new._entities = list(self._entities)
        new._scores = self._scores.copy() if self._scores is not None else None
        new._sources = {k: set(v) for k, v in self._sources.items()}
        return new

    def remove_at(self, idx: int) -> None:
        """Remove candidate at index."""
        if idx < 0 or idx >= len(self._ids):
            raise IndexError(
                f"index {idx} out of range for CandidateList of length {len(self._ids)}"
            )
        candidate_id = self._ids[idx]
        del self._ids[idx]
        if self._entities:
            del self._entities[idx]
        if self._scores is not None:
            self._scores = np.delete(self._scores, idx, axis=0)
        # Only remove from _sources if this candidate no longer appears
        if candidate_id not in self._ids:
            self._sources.pop(candidate_id, None)


class CandidateListIterator:
    def __init__(self, candidates: CandidateList):
        self.candidates = candidates
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self) -> Candidate:
        if self.index < len(self.candidates):
            c = self.candidates[self.index]
            self.index += 1
            return c
        else:
            raise StopIteration
