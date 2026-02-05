import pytest

from modules.fediway.feed import Feed, Pipeline
from modules.fediway.feed.candidates import CandidateList
from modules.fediway.feed.steps import FallbackStep, PipelineStep
from modules.fediway.sources.base import Source


class DummyStep(PipelineStep):
    def __init__(self):
        self.called = False
        self._state = {"foo": "bar"}

    def get_state(self):
        return self._state

    def set_state(self, state):
        self._state = state

    async def __call__(self, candidates: CandidateList) -> CandidateList:
        self.called = True
        # for testing, append a marker candidate
        candidates.append(999, score=1.0, source="dummy", source_group="g")
        return candidates

    def results(self):
        # return a fresh list so we can detect it
        out = CandidateList("test_entity")
        out.append(1234, score=0.5, source="r", source_group="g")
        return out


def test_feed_init():
    f = Pipeline(feature_service=None)

    assert f.feature_service is None
    assert f.steps == []
    assert f.entity is None
    assert f.counter == 0
    assert f.get_durations() == []
    assert f.is_new() is True


def test_select_and_step_and_indexing():
    f = Pipeline(feature_service=None)

    # select should set entity and return self
    ret = f.select("status_id")
    assert ret is f
    assert f.entity == "status_id"

    # register a dummy step
    ds = DummyStep()
    f.step(ds)
    assert f.steps[-1] is ds

    # __getitem__
    assert f[0] is ds
    with pytest.raises(IndexError):
        _ = f[1]


def test_get_state_and_set_state():
    f1 = Pipeline(feature_service=None)
    f1.counter = 42
    ds = DummyStep()
    f1.step(ds)
    ds._state = {"foo": "baz"}

    state = f1.get_state()

    # simulate new feed
    f2 = Pipeline(feature_service=None)
    ds2 = DummyStep()
    f2.step(ds2)
    assert ds2.get_state() == {"foo": "bar"}

    # set state
    f2.set_state(state)
    assert f2.counter == 42
    assert f2.steps[0].get_state() == {"foo": "baz"}


@pytest.mark.asyncio
async def test_execute_no_steps():
    f = Pipeline(feature_service=None)
    before = f.counter
    ret = await f.execute()

    assert isinstance(ret, CandidateList)
    assert f.counter == before + 1
    assert f.get_durations() == []


@pytest.mark.asyncio
async def test_execute_with_steps_records_durations_and_calls_steps():
    f = Pipeline(feature_service=None)
    step1 = DummyStep()
    step2 = DummyStep()
    f.step(step1)
    f.step(step2)

    before_counter = f.counter
    ret = await f.execute()
    assert isinstance(ret, CandidateList)
    assert step1.called
    assert step2.called
    assert f.counter == before_counter + 1

    durs = f.get_durations()

    assert len(durs) == 2
    assert all(isinstance(d, int) and d > 0 for d in durs)


def test_results_returns_last_step_results():
    f = Pipeline(feature_service=None)
    f.step(DummyStep())
    out = f.results()

    assert hasattr(out, "get_candidates")
    assert out.get_candidates() == [1234]


@pytest.mark.asyncio
async def test_is_new_after_execute():
    f = Pipeline(feature_service=None)

    assert f.is_new()

    f.step(DummyStep())

    assert f.is_new()

    await f.execute()

    assert not f.is_new()


class MockFallbackSource(Source):
    _tracked_params = ["name"]

    def __init__(self, name: str, candidates: list[int]):
        self.name = name
        self._candidates = candidates
        self.collect_calls = []

    def collect(self, limit: int, offset: int | None = None):
        self.collect_calls.append({"limit": limit, "offset": offset})
        return self._candidates[:limit]


def test_feed_fallback_returns_self_for_chaining():
    f = Pipeline(feature_service=None)
    source = MockFallbackSource("test", [1, 2, 3])

    result = f.fallback(source, target=10)

    assert result is f


def test_feed_fallback_adds_fallback_step():
    f = Pipeline(feature_service=None)
    source = MockFallbackSource("test", [1, 2, 3])

    f.fallback(source, target=10)

    assert len(f.steps) == 1
    assert isinstance(f.steps[0], FallbackStep)


def test_feed_fallback_uses_sample_target_when_not_specified():
    f = Pipeline(feature_service=None)
    f._sample_target = 25
    source = MockFallbackSource("test", [1, 2, 3])

    f.fallback(source)

    assert f.steps[0].target == 25


def test_feed_fallback_uses_default_when_no_sample_target():
    f = Pipeline(feature_service=None)
    source = MockFallbackSource("test", [1, 2, 3])

    f.fallback(source)

    assert f.steps[0].target == 20


def test_feed_fallback_custom_group():
    f = Pipeline(feature_service=None)
    source = MockFallbackSource("test", [1, 2, 3])

    f.fallback(source, target=10, group="trending")

    assert f.steps[0].group == "trending"


@pytest.mark.asyncio
async def test_feed_fallback_integration():
    f = Pipeline(feature_service=None)
    f.select("status_id")

    class PartialStep(PipelineStep):
        async def __call__(self, candidates: CandidateList) -> CandidateList:
            candidates.append(1, source="primary", source_group="primary")
            candidates.append(2, source="primary", source_group="primary")
            return candidates

        def results(self):
            return CandidateList("status_id")

    fallback_source = MockFallbackSource("trending", [100, 101, 102, 103, 104])

    f.step(PartialStep())
    f.fallback(fallback_source, target=5, group="trending")

    await f.execute()
    result = f.results()

    assert len(result) == 5
    assert 1 in result.get_candidates()
    assert 2 in result.get_candidates()
    assert 100 in result.get_candidates()


@pytest.mark.asyncio
async def test_feed_fallback_not_triggered_when_sufficient():
    f = Pipeline(feature_service=None)
    f.select("status_id")

    class FullStep(PipelineStep):
        async def __call__(self, candidates: CandidateList) -> CandidateList:
            for i in range(5):
                candidates.append(i, source="primary", source_group="primary")
            return candidates

        def results(self):
            return CandidateList("status_id")

    fallback_source = MockFallbackSource("trending", [100, 101, 102])

    f.step(FullStep())
    f.fallback(fallback_source, target=5)

    await f.execute()

    assert len(fallback_source.collect_calls) == 0


@pytest.mark.asyncio
async def test_feed_fallback_chaining_with_sample():
    f = Pipeline(feature_service=None)
    f.select("status_id")
    f._sample_target = 10

    fallback_source = MockFallbackSource("trending", list(range(100, 120)))

    f.fallback(fallback_source)

    await f.execute()
    result = f.results()

    assert len(result) == 10


def test_feed_is_abstract_base_class():
    from abc import ABC

    assert issubclass(Feed, ABC)
    assert Feed is not Pipeline

    # Feed should not be instantiable directly
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        Feed()


def test_pipeline_alias_in_pipeline_module():
    from modules.fediway.feed.pipeline import Feed as PipelineFeed
    from modules.fediway.feed.pipeline import Pipeline as PipelineClass

    # The alias in pipeline.py still works
    assert PipelineFeed is PipelineClass
