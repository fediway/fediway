from unittest.mock import MagicMock

import numpy as np

from modules.fediway.heuristics.diversify import DiversifyHeuristic


def test_diversify_no_shared_mutable_default():
    """Verify that seen_ids default is not shared between instances."""
    h1 = DiversifyHeuristic(by="author_id")
    h2 = DiversifyHeuristic(by="author_id")

    h1.seen_ids.add(123)

    assert 123 in h1.seen_ids
    assert 123 not in h2.seen_ids, "seen_ids should not be shared between instances"


def test_diversify_accepts_custom_seen_ids():
    h = DiversifyHeuristic(by="author_id", seen_ids={1, 2, 3})

    assert h.seen_ids == {1, 2, 3}


def test_diversify_empty_seen_ids_returns_unchanged_scores():
    h = DiversifyHeuristic(by="author_id", penalty=0.5)

    candidates = MagicMock()
    candidates.get_scores.return_value = np.array([1.0, 2.0, 3.0])

    features = MagicMock()
    features.values = np.array([[10], [20], [30]])

    result = h(candidates, features)

    np.testing.assert_array_equal(result, np.array([1.0, 2.0, 3.0]))


def test_diversify_penalizes_seen_items():
    h = DiversifyHeuristic(by="author_id", penalty=0.5, seen_ids={10, 20})

    candidates = MagicMock()
    candidates.get_scores.return_value = np.array([1.0, 2.0, 3.0])

    features = MagicMock()
    features.values = np.array([[10], [20], [30]])

    result = h(candidates, features)

    assert result[0] == 0.5  # author 10 seen, penalized
    assert result[1] == 1.0  # author 20 seen, penalized
    assert result[2] == 3.0  # author 30 not seen, unchanged


def test_diversify_update_seen():
    h = DiversifyHeuristic(by="author_id")

    candidate = MagicMock()
    h.update_seen(candidate, [42])

    assert 42 in h.seen_ids


def test_diversify_get_set_state():
    h = DiversifyHeuristic(by="author_id", seen_ids={1, 2, 3})

    state = h.get_state()
    assert set(state["seen_ids"]) == {1, 2, 3}

    h2 = DiversifyHeuristic(by="author_id")
    h2.set_state(state)
    assert h2.seen_ids == {1, 2, 3}


def test_diversify_empty_candidates_returns_empty():
    h = DiversifyHeuristic(by="author_id", seen_ids={1, 2})

    candidates = MagicMock()
    candidates.get_scores.return_value = np.array([])

    features = MagicMock()

    result = h(candidates, features)

    assert len(result) == 0
