import json

import numpy as np
import pytest

from modules.fediway.feed import Candidate, CandidateList


def test_candidates_init():
    entity = "status_id"
    candidates = CandidateList(entity)

    assert candidates.entity == entity
    assert candidates.get_candidates() == []
    assert candidates._scores is None
    assert candidates._sources == {}


def test_append_with_candidate():
    candidates = CandidateList("status_id")

    candidates.append(123, score=0.8, source="source1", source_group="group1")

    assert len(candidates) == 1
    assert candidates.get_candidates() == [123]
    assert list(candidates.get_scores()) == [0.8]
    assert candidates._sources[123] == {("source1", "group1")}


def test_append_with_list_sources():
    candidates = CandidateList("status_id")

    sources = ["source1", "source2"]
    groups = ["group1", "group2"]

    candidates.append(123, source=sources, source_group=groups)

    expected_sources = {("source1", "group1"), ("source2", "group2")}
    assert candidates._sources[123] == expected_sources


def test_append_with_no_source():
    candidates = CandidateList("status_id")

    candidates.append(1, score=0.5)

    assert candidates._sources[1] == set()


def test_append_duplicate_candidate():
    candidates = CandidateList("status_id")

    candidates.append(1, source="source1", source_group="group1")
    candidates.append(1, source="source2", source_group="group2")

    assert len(candidates) == 2  # Both entries are kept
    expected_sources = {("source1", "group1"), ("source2", "group2")}
    assert candidates.get_source(1) == expected_sources


def test_get_state():
    candidates = CandidateList("status_id")
    candidates.append(1, score=0.8, source="source1", source_group="group1")
    candidates.append(2, score=0.9, source="source2", source_group="group2")

    state = candidates.get_state()

    assert state["ids"] == [1, 2]
    assert state["scores"] == [0.8, 0.9]
    assert state["sources"][1] == [("source1", "group1")]
    assert state["sources"][2] == [("source2", "group2")]


def test_set_state():
    candidates = CandidateList("status_id")

    state = {
        "ids": [1, 2],
        "scores": [0.7, 0.8],
        "sources": {
            1: [("source1", "group1")],
            2: [("source2", "group2")],
        },
    }

    candidates.set_state(state)

    assert candidates._ids == [1, 2]
    assert list(candidates.get_scores()) == [0.7, 0.8]
    assert candidates._sources[1] == {("source1", "group1")}
    assert candidates._sources[2] == {("source2", "group2")}


def test_set_json_serialized_state_with_integer_entities():
    candidates = CandidateList("status_id")

    state = {
        "ids": [1, 2],
        "scores": [0.7, 0.8],
        "sources": {
            1: [("source1", "group1")],
            2: [("source2", "group2")],
        },
    }

    candidates.set_state(json.loads(json.dumps(state)))

    assert candidates.get_candidates() == [1, 2]
    assert list(candidates.get_scores()) == [0.7, 0.8]
    assert candidates.get_source(1) == {("source1", "group1")}
    assert candidates.get_source(2) == {("source2", "group2")}


def test_set_json_serialized_state_with_string_entities():
    candidates = CandidateList("status_id")

    state = {
        "ids": ["a", "b"],
        "scores": [0.7, 0.8],
        "sources": {
            "a": [("source1", "group1")],
            "b": [("source2", "group2")],
        },
    }

    candidates.set_state(json.loads(json.dumps(state)))

    assert candidates.get_candidates() == ["a", "b"]
    assert list(candidates.get_scores()) == [0.7, 0.8]
    assert candidates.get_source("a") == {("source1", "group1")}
    assert candidates.get_source("b") == {("source2", "group2")}


def test_unique_groups():
    candidates = CandidateList("status_id")

    candidates.append(1, source="source1", source_group="group1")
    candidates.append(2, source="source2", source_group="group2")
    candidates.append(3, source="source3", source_group="group1")

    groups = candidates.unique_groups()

    assert groups == {"group1", "group2"}


def test_get_entity_rows():
    candidates = CandidateList("account_id")

    candidates.append(1)
    candidates.append(5)

    rows = candidates.get_entity_rows()

    expected_rows = [{"account_id": 1}, {"account_id": 5}]
    assert rows == expected_rows


def test_getitem_index_returns_candidate():
    candidates = CandidateList("status_id")
    candidates.append(101, score=0.9, source="source1", source_group="groupA")

    candidate = candidates[0]

    assert isinstance(candidate, Candidate)
    assert candidate.entity == "status_id"
    assert candidate.id == 101
    assert candidate.score == 0.9
    assert candidate.sources == {("source1", "groupA")}


def test_getitem_index_with_multiple_candidates():
    candidates = CandidateList("status_id")
    candidates.append(1, score=0.5, source="sourceA", source_group="groupA")
    candidates.append(2, score=0.7, source="sourceB", source_group="groupB")

    candidate = candidates[1]

    assert candidate.id == 2
    assert candidate.score == 0.7
    assert candidate.sources == {("sourceB", "groupB")}


def test_getitem_slice_returns_candidate_list():
    candidates = CandidateList("status_id")
    candidates.append(1, score=0.1, source="source1", source_group="g1")
    candidates.append(2, score=0.2, source="source2", source_group="g2")
    candidates.append(3, score=0.3, source="source3", source_group="g3")

    sliced = candidates[0:2]

    assert isinstance(sliced, CandidateList)
    assert len(sliced) == 2
    assert sliced.get_candidates() == [1, 2]
    assert list(sliced.get_scores()) == [0.1, 0.2]
    assert sliced.get_source(1) == {("source1", "g1")}
    assert sliced.get_source(2) == {("source2", "g2")}


def test_getitem_index_with_missing_source():
    candidates = CandidateList("status_id")

    candidates._ids.append(123)
    candidates._entities.append("status_id")
    candidates._scores = np.array([0.5])

    candidate = candidates[0]

    assert isinstance(candidate, Candidate)
    assert candidate.id == 123
    assert candidate.score == 0.5
    assert candidate.sources == set()


def test_getitem_slice_preserves_entity():
    candidates = CandidateList("user_id")
    candidates.append(42)
    sliced = candidates[:1]

    assert isinstance(sliced, CandidateList)
    assert sliced.entity == "user_id"


def test_getitem_out_of_bounds_raises_index_error():
    candidates = CandidateList("status_id")
    candidates.append(1)

    with pytest.raises(IndexError):
        _ = candidates[5]


def test_getitem_slice_empty():
    candidates = CandidateList("status_id")
    candidates.append(1)
    result = candidates[10:20]  # Out of bounds but valid slice

    assert isinstance(result, CandidateList)
    assert len(result) == 0
    assert result.get_candidates() == []


def test_getitem_with_numpy_index_array():
    candidates = CandidateList("status_id")
    candidates.append(1, score=0.1, source="s1", source_group="g1")
    candidates.append(2, score=0.2, source="s2", source_group="g2")
    candidates.append(3, score=0.3, source="s3", source_group="g3")

    idx = np.array([0, 2])
    result = candidates[idx]

    assert isinstance(result, CandidateList)
    assert result.get_candidates() == [1, 3]
    assert list(result.get_scores()) == [0.1, 0.3]
    assert result.get_source(1) == {("s1", "g1")}
    assert result.get_source(3) == {("s3", "g3")}


def test_getitem_with_numpy_boolean_mask():
    candidates = CandidateList("status_id")
    candidates.append(1, score=0.1, source="s1", source_group="g1")
    candidates.append(2, score=0.2, source="s2", source_group="g2")
    candidates.append(3, score=0.3, source="s3", source_group="g3")

    mask = np.array([True, False, True])
    result = candidates[mask]

    assert isinstance(result, CandidateList)
    assert result.get_candidates() == [1, 3]
    assert list(result.get_scores()) == [0.1, 0.3]


def test_iadd_combines_candidate_lists():
    cl1 = CandidateList("status_id")
    cl1.append(1, score=0.5, source="s1", source_group="g1")
    cl1.append(2, score=0.6, source="s2", source_group="g2")

    cl2 = CandidateList("status_id")
    cl2.append(3, score=0.7, source="s3", source_group="g3")
    cl2.append(4, score=0.8, source="s4", source_group="g4")

    cl1 += cl2

    assert cl1.get_candidates() == [1, 2, 3, 4]
    assert list(cl1.get_scores()) == [0.5, 0.6, 0.7, 0.8]
    assert cl1.get_source(3) == {("s3", "g3")}
    assert cl1.get_source(4) == {("s4", "g4")}


def test_iadd_merges_sources_for_existing_candidate():
    cl1 = CandidateList("status_id")
    cl1.append(1, score=0.5, source="s1", source_group="g1")

    cl2 = CandidateList("status_id")
    cl2.append(1, score=0.6, source="s2", source_group="g2")

    cl1 += cl2

    assert cl1.get_candidates() == [1, 1]  # both are kept in the list
    assert list(cl1.get_scores()) == [0.5, 0.6]
    assert cl1.get_source(1) == {("s1", "g1"), ("s2", "g2")}


def test_iadd_preserves_entity():
    cl1 = CandidateList("user_id")
    cl2 = CandidateList("user_id")
    cl2.append(5)

    cl1 += cl2

    assert cl1.entity == "user_id"
    assert cl1.get_candidates() == [5]


def test_iadd_raises_on_mismatched_types():
    cl1 = CandidateList("status_id")
    cl1.append(1)

    with pytest.raises(TypeError, match="Cannot add str to CandidateList"):
        cl1 += "not_a_candidate_list"


def test_index_returns_correct_position():
    cl = CandidateList("status_id")
    cl.append(100)
    cl.append(200)
    cl.append(300)

    assert cl.index(100) == 0
    assert cl.index(200) == 1
    assert cl.index(300) == 2


def test_index_with_duplicates_returns_first_occurrence():
    cl = CandidateList("status_id")
    cl.append(100)
    cl.append(200)
    cl.append(100)  # duplicate

    assert cl.index(100) == 0  # First match
    assert cl.index(200) == 1


def test_index_raises_for_missing_candidate():
    cl = CandidateList("status_id")
    cl.append(1)
    cl.append(2)

    with pytest.raises(ValueError):
        cl.index(999)  # not in the list


def test_copy_creates_independent_copy():
    cl = CandidateList("status_id")
    cl.append(1, score=0.5, source="s1", source_group="g1")
    cl.append(2, score=0.6, source="s2", source_group="g2")

    copy = cl.copy()

    assert copy.entity == cl.entity
    assert copy.get_candidates() == [1, 2]
    assert list(copy.get_scores()) == [0.5, 0.6]
    assert copy.get_source(1) == {("s1", "g1")}

    # Modify original, copy should be unaffected
    cl.append(3, score=0.7, source="s3", source_group="g3")
    assert len(cl) == 3
    assert len(copy) == 2


def test_copy_creates_independent_sources():
    cl = CandidateList("status_id")
    cl.append(1, source="s1", source_group="g1")

    copy = cl.copy()

    # Modify original sources
    cl._sources[1].add(("s2", "g2"))

    # Copy should be unaffected
    assert copy.get_source(1) == {("s1", "g1")}


def test_copy_empty_list():
    cl = CandidateList("status_id")
    copy = cl.copy()

    assert len(copy) == 0
    assert copy.entity == "status_id"


def test_remove_at_removes_candidate_at_index():
    cl = CandidateList("status_id")
    cl.append(1, score=0.1, source="s1", source_group="g1")
    cl.append(2, score=0.2, source="s2", source_group="g2")
    cl.append(3, score=0.3, source="s3", source_group="g3")

    cl.remove_at(1)

    assert len(cl) == 2
    assert cl.get_candidates() == [1, 3]
    assert list(cl.get_scores()) == [0.1, 0.3]
    assert 2 not in cl._sources


def test_remove_at_first_element():
    cl = CandidateList("status_id")
    cl.append(1, score=0.1, source="s1", source_group="g1")
    cl.append(2, score=0.2, source="s2", source_group="g2")

    cl.remove_at(0)

    assert cl.get_candidates() == [2]
    assert list(cl.get_scores()) == [0.2]


def test_remove_at_last_element():
    cl = CandidateList("status_id")
    cl.append(1, score=0.1, source="s1", source_group="g1")
    cl.append(2, score=0.2, source="s2", source_group="g2")

    cl.remove_at(1)

    assert cl.get_candidates() == [1]
    assert list(cl.get_scores()) == [0.1]


def test_remove_at_keeps_sources_for_duplicate_ids():
    cl = CandidateList("status_id")
    cl.append(1, score=0.1, source="s1", source_group="g1")
    cl.append(1, score=0.2, source="s2", source_group="g2")  # duplicate id

    cl.remove_at(0)  # Remove first occurrence

    assert cl.get_candidates() == [1]
    # Sources should still be present since id 1 still exists
    assert 1 in cl._sources


def test_remove_at_out_of_bounds_raises():
    cl = CandidateList("status_id")
    cl.append(1)

    with pytest.raises(IndexError):
        cl.remove_at(5)

    with pytest.raises(IndexError):
        cl.remove_at(-1)


def test_iteration_with_for_loop():
    cl = CandidateList("status_id")
    cl.append(1, score=0.9, source="s1", source_group="g1")
    cl.append(2, score=0.8, source="s2", source_group="g2")
    cl.append(3, score=0.7, source="s3", source_group="g3")

    ids = [c.id for c in cl]

    assert ids == [1, 2, 3]


def test_iteration_yields_candidate_objects():
    cl = CandidateList("status_id")
    cl.append(100, score=0.5, source="src", source_group="grp")

    for c in cl:
        assert isinstance(c, Candidate)
        assert c.id == 100
        assert c.score == 0.5
        assert c.sources == {("src", "grp")}


def test_iteration_with_list_conversion():
    cl = CandidateList("status_id")
    cl.append(1)
    cl.append(2)

    candidates = list(cl)

    assert len(candidates) == 2
    assert all(isinstance(c, Candidate) for c in candidates)


def test_iteration_empty_list():
    cl = CandidateList("status_id")

    result = list(cl)

    assert result == []


def test_iterator_is_iterable():
    cl = CandidateList("status_id")
    cl.append(1)

    iterator = iter(cl)
    assert iter(iterator) is iterator


# Multi-entity tests


def test_init_with_multiple_entity_types():
    cl = CandidateList(["status_id", "account_id"])

    assert cl.entity == "status_id"  # Primary entity
    assert cl.entity_types == ["status_id", "account_id"]


def test_append_with_explicit_entity():
    cl = CandidateList(["status_id", "account_id"])

    cl.append(1, entity="status_id")
    cl.append(2, entity="account_id")

    assert cl._entities == ["status_id", "account_id"]


def test_append_rejects_invalid_entity():
    cl = CandidateList(["status_id", "account_id"])

    with pytest.raises(ValueError, match="Entity type 'tag_id' not in allowed types"):
        cl.append(1, entity="tag_id")


def test_candidate_has_correct_entity():
    cl = CandidateList(["status_id", "account_id"])

    cl.append(1, entity="status_id")
    cl.append(2, entity="account_id")

    assert cl[0].entity == "status_id"
    assert cl[1].entity == "account_id"


def test_get_entity_rows_with_mixed_entities():
    cl = CandidateList(["status_id", "account_id"])

    cl.append(123, entity="status_id")
    cl.append(456, entity="account_id")

    rows = cl.get_entity_rows()

    assert rows == [{"status_id": 123}, {"account_id": 456}]


def test_entity_preserved_in_slice():
    cl = CandidateList(["status_id", "account_id"])
    cl.append(1, entity="status_id")
    cl.append(2, entity="account_id")
    cl.append(3, entity="status_id")

    sliced = cl[1:3]

    assert sliced._entities == ["account_id", "status_id"]
    assert sliced[0].entity == "account_id"


def test_entities_in_state_serialization():
    cl = CandidateList(["status_id", "account_id"])
    cl.append(1, entity="status_id")
    cl.append(2, entity="account_id")

    state = cl.get_state()

    assert state["entities"] == ["status_id", "account_id"]


def test_entities_restored_from_state():
    cl = CandidateList(["status_id", "account_id"])

    state = {
        "ids": [1, 2],
        "entities": ["status_id", "account_id"],
        "scores": [1.0, 1.0],
        "sources": {},
    }

    cl.set_state(state)

    assert cl._entities == ["status_id", "account_id"]
    assert cl[0].entity == "status_id"
    assert cl[1].entity == "account_id"


def test_backwards_compat_state_without_entities():
    cl = CandidateList("status_id")

    # Old state format without entities field
    state = {
        "ids": [1, 2],
        "scores": [0.5, 0.6],
        "sources": {1: [], 2: []},
    }

    cl.set_state(state)

    # Should default to primary entity
    assert cl._entities == ["status_id", "status_id"]


def test_iadd_preserves_entities():
    cl1 = CandidateList(["status_id", "account_id"])
    cl1.append(1, entity="status_id")

    cl2 = CandidateList(["status_id", "account_id"])
    cl2.append(2, entity="account_id")

    cl1 += cl2

    assert cl1._entities == ["status_id", "account_id"]


def test_none_entity_creates_empty_types():
    cl = CandidateList(None)

    assert cl.entity is None
    assert cl.entity_types == []


def test_entity_types_property():
    cl = CandidateList(["status_id", "account_id", "tag_id"])

    assert cl.entity_types == ["status_id", "account_id", "tag_id"]


# Vector score tests


def test_set_scores_with_vectors():
    cl = CandidateList("status_id")
    cl.append(1)
    cl.append(2)

    # Set 2D vector scores (e.g., embeddings)
    embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    cl.set_scores(embeddings)

    scores = cl.get_scores()
    assert scores.shape == (2, 3)
    assert np.allclose(scores[0], [0.1, 0.2, 0.3])
    assert np.allclose(scores[1], [0.4, 0.5, 0.6])


def test_candidate_vector_score():
    cl = CandidateList("status_id")
    cl.append(1)
    cl.append(2)

    embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    cl.set_scores(embeddings)

    candidate = cl[0]
    assert isinstance(candidate.score, np.ndarray)
    assert np.allclose(candidate.score, [0.1, 0.2, 0.3])


def test_vector_scores_preserved_in_slice():
    cl = CandidateList("status_id")
    cl.append(1)
    cl.append(2)
    cl.append(3)

    embeddings = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
    cl.set_scores(embeddings)

    sliced = cl[0:2]
    scores = sliced.get_scores()

    assert scores.shape == (2, 2)
    assert np.allclose(scores[0], [0.1, 0.2])
    assert np.allclose(scores[1], [0.3, 0.4])


def test_vector_scores_in_state_serialization():
    cl = CandidateList("status_id")
    cl.append(1)
    cl.append(2)

    embeddings = np.array([[0.1, 0.2], [0.3, 0.4]])
    cl.set_scores(embeddings)

    state = cl.get_state()

    # Should serialize as nested list
    assert state["scores"] == [[0.1, 0.2], [0.3, 0.4]]


def test_vector_scores_restored_from_state():
    cl = CandidateList("status_id")

    state = {
        "ids": [1, 2],
        "entities": ["status_id", "status_id"],
        "scores": [[0.1, 0.2], [0.3, 0.4]],
        "sources": {},
    }

    cl.set_state(state)

    scores = cl.get_scores()
    assert scores.shape == (2, 2)
    assert np.allclose(scores[0], [0.1, 0.2])
