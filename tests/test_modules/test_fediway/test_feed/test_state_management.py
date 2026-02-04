"""
Tests for Feed state management: bounds, get/set state, trimming.
"""

import pytest

from modules.fediway.feed import Feed
from modules.fediway.feed.base import MAX_REMEMBERED_ITEMS, MAX_SEEN_ITEMS
from modules.fediway.sources.base import Source


class SimpleSource(Source):
    _tracked_params = []
    _id = "simple"

    def __init__(self, items):
        self.items = items

    def collect(self, limit: int):
        return self.items[:limit]


class SimpleFeed(Feed):
    entity = "test_id"

    def __init__(self, items=None, feature_service=None):
        super().__init__(feature_service=feature_service)
        self._items = items or list(range(100))

    def sources(self):
        return {"main": [(SimpleSource(self._items), 50)]}

    async def forward(self, candidates):
        return candidates


def test_state_bounds_constants():
    assert MAX_SEEN_ITEMS == 500
    assert MAX_REMEMBERED_ITEMS == 200


@pytest.mark.asyncio
async def test_trim_state_seen():
    feed = SimpleFeed()
    feed._seen = set(range(1000))

    feed._trim_state()

    assert len(feed._seen) == MAX_SEEN_ITEMS


@pytest.mark.asyncio
async def test_trim_state_remembered():
    feed = SimpleFeed()
    for i in range(500):
        feed._remembered.append(i, source="test", source_group="test")

    feed._trim_state()

    assert len(feed._remembered) == MAX_REMEMBERED_ITEMS


@pytest.mark.asyncio
async def test_trim_state_preserves_small_state():
    feed = SimpleFeed()
    feed._seen = set(range(100))
    for i in range(50):
        feed._remembered.append(i, source="test", source_group="test")

    feed._trim_state()

    assert len(feed._seen) == 100
    assert len(feed._remembered) == 50


def test_get_state_returns_serializable():
    feed = SimpleFeed()
    feed._seen = {1, 2, 3}
    feed._remembered.append(10, score=0.9, source="s1", source_group="g1")
    feed._heuristic_states = {"test": {"value": 42}}

    state = feed.get_state()

    assert set(state["seen"]) == {1, 2, 3}
    assert state["remembered"]["ids"] == [10]
    assert state["heuristics"] == {"test": {"value": 42}}


def test_set_state_restores_feed():
    stored_state = {
        "seen": [1, 2, 3],
        "remembered": {
            "ids": [10, 20, 30],
            "scores": [1.0, 0.9, 0.8],
            "sources": {"10": [["s1", "g1"]], "20": [["s2", "g2"]], "30": [["s3", "g3"]]},
        },
        "heuristics": {"test": {"value": 42}},
    }

    feed = SimpleFeed()
    feed.set_state(stored_state)

    assert feed._seen == {1, 2, 3}
    assert len(feed._remembered) == 3
    assert feed._heuristic_states == {"test": {"value": 42}}


def test_get_set_state_roundtrip():
    feed1 = SimpleFeed()
    feed1._seen = {100, 200, 300}
    feed1._remembered.append(1, score=0.5, source="src", source_group="grp")
    feed1._heuristic_states = {"h1": {"count": 5}}

    state = feed1.get_state()

    feed2 = SimpleFeed()
    feed2.set_state(state)

    assert feed2._seen == feed1._seen
    assert len(feed2._remembered) == len(feed1._remembered)
    assert feed2._heuristic_states == feed1._heuristic_states


@pytest.mark.asyncio
async def test_is_new_empty_remembered():
    feed = SimpleFeed()
    assert feed.is_new() is True


@pytest.mark.asyncio
async def test_is_new_with_remembered():
    feed = SimpleFeed()
    feed._remembered.append(1, source="test", source_group="test")
    assert feed.is_new() is False


@pytest.mark.asyncio
async def test_collect_adds_to_remembered():
    feed = SimpleFeed()

    await feed.collect()

    assert len(feed._remembered) > 0


@pytest.mark.asyncio
async def test_collect_appends_to_existing():
    feed = SimpleFeed(items=list(range(100, 200)))
    feed._remembered.append(1, source="initial", source_group="test")
    initial_count = len(feed._remembered)

    await feed.collect()

    assert len(feed._remembered) > initial_count


@pytest.mark.asyncio
async def test_collect_trims_state():
    feed = SimpleFeed()
    feed._seen = set(range(1000))

    await feed.collect()

    assert len(feed._seen) == MAX_SEEN_ITEMS


@pytest.mark.asyncio
async def test_execute_collects_when_new():
    feed = SimpleFeed()
    assert feed.is_new() is True

    result = await feed.execute(limit=10)

    assert len(result) == 10
    assert len(feed._remembered) > 0


@pytest.mark.asyncio
async def test_execute_skips_collect_when_has_state():
    feed = SimpleFeed()
    # Pre-populate remembered
    for i in range(50):
        feed._remembered.append(i, source="pre", source_group="pre")

    result = await feed.execute(limit=10)

    # Should return from existing remembered, not collect new
    assert len(result) == 10
    assert result[0].id == 0


@pytest.mark.asyncio
async def test_execute_updates_seen():
    feed = SimpleFeed()

    result = await feed.execute(limit=10)

    assert len(feed._seen) == len(result)
    for c in result:
        assert c.id in feed._seen


@pytest.mark.asyncio
async def test_execute_pagination_with_max_id():
    feed = SimpleFeed()
    # Pre-populate
    for i in range(50):
        feed._remembered.append(i, source="test", source_group="test")

    result = await feed.execute(max_id=10, limit=5)

    assert len(result) == 5
    assert result[0].id == 11


@pytest.mark.asyncio
async def test_execute_pagination_with_offset():
    feed = SimpleFeed()
    # Pre-populate
    for i in range(50):
        feed._remembered.append(i, source="test", source_group="test")

    result = await feed.execute(offset=20, limit=5)

    assert len(result) == 5
    assert result[0].id == 20


def test_flush_clears_local_state():
    feed = SimpleFeed()
    feed._seen = {1, 2, 3}
    feed._remembered.append(1, source="test", source_group="test")
    feed._heuristic_states = {"test": "value"}

    feed.flush()

    assert len(feed._seen) == 0
    assert len(feed._remembered) == 0
    assert feed._heuristic_states == {}
