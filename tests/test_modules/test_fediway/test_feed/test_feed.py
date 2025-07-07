import pytest
import asyncio
import time
from datetime import datetime

from modules.fediway.feed import Feed
from modules.fediway.feed.steps import PipelineStep
from modules.fediway.feed.candidates import CandidateList


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
    f = Feed(feature_service=None)

    assert f.feature_service is None
    assert f.steps == []
    assert f.entity is None
    assert f.counter == 0
    assert f.get_durations() == []
    assert f.is_new() is True


def test_select_and_step_and_indexing():
    f = Feed(feature_service=None)

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
    f1 = Feed(feature_service=None)
    f1.counter = 42
    ds = DummyStep()
    f1.step(ds)
    ds._state = {"foo": "baz"}

    state = f1.get_state()

    # simulate new feed
    f2 = Feed(feature_service=None)
    ds2 = DummyStep()
    f2.step(ds2)
    assert ds2.get_state() == {"foo": "bar"}

    # set state
    f2.set_state(state)
    assert f2.counter == 42
    assert f2.steps[0].get_state() == {"foo": "baz"}


@pytest.mark.asyncio
async def test_execute_no_steps():
    f = Feed(feature_service=None)
    before = f.counter
    ret = await f.execute()

    assert ret is f
    assert f.counter == before + 1
    assert f.get_durations() == []


@pytest.mark.asyncio
async def test_execute_with_steps_records_durations_and_calls_steps():
    f = Feed(feature_service=None)
    step1 = DummyStep()
    step2 = DummyStep()
    f.step(step1)
    f.step(step2)

    before_counter = f.counter
    ret = await f.execute()
    assert ret is f
    assert step1.called
    assert step2.called
    assert f.counter == before_counter + 1

    durs = f.get_durations()

    assert len(durs) == 2
    assert all(isinstance(d, int) and d > 0 for d in durs)


def test_results_returns_last_step_results():
    f = Feed(feature_service=None)
    f.step(DummyStep())
    out = f.results()

    assert hasattr(out, "get_candidates")
    assert out.get_candidates() == [1234]


def test_is_new_after_execute():
    f = Feed(feature_service=None)

    assert f.is_new()

    f.step(DummyStep())

    assert f.is_new()

    asyncio.get_event_loop().run_until_complete(f.execute())

    assert not f.is_new()
