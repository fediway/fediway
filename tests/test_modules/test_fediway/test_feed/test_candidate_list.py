from modules.fediway.feed import Candidate, CandidateList
import json


def test_candidates_init():
    entity = "status_id"
    candidates = CandidateList(entity)

    assert candidates.entity == entity
    assert candidates._ids == []
    assert candidates._scores == []
    assert candidates._sources == {}


def test_append_with_candidate():
    candidates = CandidateList("status_id")

    candidates.append(123, score=0.8, source="source1", source_group="group1")

    assert len(candidates) == 1
    assert candidates._ids == [123]
    assert candidates._scores == [0.8]
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
    assert candidates._sources[1] == expected_sources


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
    assert candidates._scores == [0.7, 0.8]
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

    assert candidates._ids == [1, 2]
    assert candidates._scores == [0.7, 0.8]
    assert candidates._sources[1] == {("source1", "group1")}
    assert candidates._sources[2] == {("source2", "group2")}


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

    assert candidates._ids == ["a", "b"]
    assert candidates._scores == [0.7, 0.8]
    assert candidates._sources["a"] == {("source1", "group1")}
    assert candidates._sources["b"] == {("source2", "group2")}


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
