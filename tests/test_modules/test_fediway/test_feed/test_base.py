import pytest

from modules.fediway.feed import Feed
from modules.fediway.feed.candidates import CandidateList
from modules.fediway.sources.base import Source


class MockSource(Source):
    _tracked_params = ["name"]

    def __init__(self, name: str, candidates: list[int]):
        self.name = name
        self._candidates = candidates

    def collect(self, limit: int, offset: int | None = None):
        return self._candidates[:limit]


class SimpleFeed(Feed):
    entity = "status_id"

    def __init__(self, sources_dict=None, **kwargs):
        super().__init__(**kwargs)
        self._sources_dict = sources_dict or {}

    def sources(self):
        return self._sources_dict

    async def process(self, candidates):
        return candidates


class SampleFeed(Feed):
    entity = "status_id"

    def __init__(self, sources_dict=None, sample_n=10, **kwargs):
        super().__init__(**kwargs)
        self._sources_dict = sources_dict or {}
        self._sample_n = sample_n

    def sources(self):
        return self._sources_dict

    async def process(self, candidates):
        candidates = self.unique(candidates)
        return self.sample(candidates, n=self._sample_n)


def test_feed_is_abstract():
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        Feed()


def test_feed_requires_sources_implementation():
    class MissingSources(Feed):
        async def process(self, candidates):
            return candidates

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        MissingSources()


def test_feed_requires_process_implementation():
    class MissingProcess(Feed):
        def sources(self):
            return {}

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        MissingProcess()


def test_simple_feed_instantiation():
    feed = SimpleFeed()
    assert feed.entity == "status_id"
    assert feed._feature_service is None


@pytest.mark.asyncio
async def test_execute_with_empty_sources():
    feed = SimpleFeed(sources_dict={})
    results = await feed.execute(limit=10)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_execute_collects_from_sources():
    source = MockSource("test", [1, 2, 3, 4, 5])
    feed = SimpleFeed(sources_dict={"main": [(source, 10)]})

    results = await feed.execute(limit=10)

    assert len(results) == 5
    assert set(results.get_candidates()) == {1, 2, 3, 4, 5}


@pytest.mark.asyncio
async def test_execute_with_multiple_groups():
    source1 = MockSource("s1", [1, 2, 3])
    source2 = MockSource("s2", [4, 5, 6])

    feed = SimpleFeed(
        sources_dict={
            "group1": [(source1, 10)],
            "group2": [(source2, 10)],
        }
    )

    results = await feed.execute(limit=20)

    assert len(results) == 6
    assert set(results.get_candidates()) == {1, 2, 3, 4, 5, 6}


@pytest.mark.asyncio
async def test_process_receives_collected_candidates():
    source = MockSource("test", [1, 2, 3])
    received_candidates = []

    class CapturingFeed(Feed):
        entity = "status_id"

        def sources(self):
            return {"main": [(source, 10)]}

        async def process(self, candidates):
            received_candidates.append(candidates)
            return candidates

    feed = CapturingFeed()
    await feed.execute(limit=10)

    assert len(received_candidates) == 1
    assert len(received_candidates[0]) == 3


@pytest.mark.asyncio
async def test_process_return_none_raises_error():
    class BadFeed(Feed):
        entity = "status_id"

        def sources(self):
            return {}

        async def process(self, candidates):
            pass

    feed = BadFeed()
    with pytest.raises(RuntimeError, match="returned None"):
        await feed.execute()


def test_validate_sources_wrong_type():
    class BadSourcesFeed(Feed):
        entity = "status_id"

        def sources(self):
            return "not a dict"

        async def process(self, candidates):
            return candidates

    feed = BadSourcesFeed()
    with pytest.raises(TypeError, match="must return dict"):
        feed._build_pipeline()


def test_validate_sources_wrong_item_type():
    class BadSourcesFeed(Feed):
        entity = "status_id"

        def sources(self):
            return {"main": "not a list"}

        async def process(self, candidates):
            return candidates

    feed = BadSourcesFeed()
    with pytest.raises(TypeError, match="must be list"):
        feed._build_pipeline()


def test_validate_sources_wrong_tuple():
    class BadSourcesFeed(Feed):
        entity = "status_id"

        def sources(self):
            return {"main": ["not a tuple"]}

        async def process(self, candidates):
            return candidates

    feed = BadSourcesFeed()
    with pytest.raises(TypeError, match="must be.*tuple"):
        feed._build_pipeline()


def test_unique_removes_duplicates():
    feed = SimpleFeed()
    candidates = CandidateList("status_id")
    candidates.append(1, source="s1", source_group="g1")
    candidates.append(2, source="s1", source_group="g1")
    candidates.append(1, source="s2", source_group="g2")
    candidates.append(3, source="s1", source_group="g1")

    result = feed.unique(candidates)

    assert len(result) == 3
    assert result.get_candidates() == [1, 2, 3]


def test_unique_empty_list():
    feed = SimpleFeed()
    candidates = CandidateList("status_id")
    result = feed.unique(candidates)
    assert len(result) == 0


def test_sample_respects_n():
    feed = SimpleFeed()
    candidates = CandidateList("status_id")
    for i in range(10):
        candidates.append(i, score=1.0, source="s", source_group="g")

    result = feed.sample(candidates, n=3)

    assert len(result) == 3


def test_sample_with_fewer_candidates():
    feed = SimpleFeed()
    candidates = CandidateList("status_id")
    candidates.append(1, score=1.0, source="s", source_group="g")
    candidates.append(2, score=1.0, source="s", source_group="g")

    result = feed.sample(candidates, n=10)

    assert len(result) == 2


def test_sample_empty_list():
    feed = SimpleFeed()
    candidates = CandidateList("status_id")
    result = feed.sample(candidates, n=5)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_pagination_with_offset():
    source = MockSource("test", list(range(100)))
    feed = SampleFeed(sources_dict={"main": [(source, 100)]}, sample_n=50)

    page1 = await feed.execute(limit=10)
    page2 = await feed.execute(offset=10, limit=10)

    assert len(page1) == 10
    assert len(page2) == 10
    assert set(page1.get_candidates()).isdisjoint(set(page2.get_candidates()))


@pytest.mark.asyncio
async def test_pagination_with_max_id():
    source = MockSource("test", list(range(1, 101)))
    feed = SampleFeed(sources_dict={"main": [(source, 100)]}, sample_n=50)

    page1 = await feed.execute(limit=10)
    last_id = page1.get_candidates()[-1]
    page2 = await feed.execute(max_id=last_id, limit=10)

    assert len(page1) == 10
    assert len(page2) == 10
    assert last_id not in page2.get_candidates()


def test_flush_clears_state():
    feed = SimpleFeed()
    feed._seen = {1, 2, 3}
    feed._remembered.append(1)
    feed._heuristic_states = {"key": "value"}

    feed.flush()

    assert feed._seen == set()
    assert len(feed._remembered) == 0
    assert feed._heuristic_states == {}


@pytest.mark.asyncio
async def test_fallback_triggered_when_insufficient():
    main_source = MockSource("main", [1, 2])
    fallback_source = MockSource("fallback", [10, 11, 12, 13, 14])

    class FallbackFeed(SimpleFeed):
        def get_min_candidates(self):
            return 5

    feed = FallbackFeed(
        sources_dict={
            "main": [(main_source, 10)],
            "_fallback": [(fallback_source, 10)],
        }
    )

    results = await feed.execute(limit=20)

    all_ids = set(results.get_candidates())
    assert 1 in all_ids
    assert 2 in all_ids
    assert any(id >= 10 for id in all_ids)


@pytest.mark.asyncio
async def test_fallback_not_triggered_when_sufficient():
    main_source = MockSource("main", [1, 2, 3, 4, 5])
    fallback_source = MockSource("fallback", [100, 101])

    class FallbackFeed(SimpleFeed):
        def get_min_candidates(self):
            return 3

    feed = FallbackFeed(
        sources_dict={
            "main": [(main_source, 10)],
            "_fallback": [(fallback_source, 10)],
        }
    )

    results = await feed.execute(limit=20)

    all_ids = set(results.get_candidates())
    assert all_ids == {1, 2, 3, 4, 5}


@pytest.mark.asyncio
async def test_pipeline_property():
    feed = SimpleFeed(sources_dict={"main": [(MockSource("m", [1]), 10)]})

    assert feed.pipeline is None

    await feed.execute(limit=10)

    assert feed.pipeline is not None


def test_get_min_candidates_default():
    feed = SimpleFeed()
    assert feed.get_min_candidates() == 10
