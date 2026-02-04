import pytest

from modules.fediway.feed.candidates import CandidateList
from modules.fediway.feed.steps import FallbackStep, SourcingStep
from modules.fediway.sources.base import Source


class MockSource(Source):
    _tracked_params = ["name"]

    def __init__(self, name: str, candidates: list[int]):
        self.name = name
        self._candidates = candidates
        self.collect_calls = []

    def collect(self, limit: int, offset: int | None = None):
        self.collect_calls.append({"limit": limit, "offset": offset})
        return self._candidates[:limit]


class EmptySource(Source):
    _tracked_params = []

    def collect(self, limit: int, offset: int | None = None):
        return []


class FailingSource(Source):
    _tracked_params = []

    def collect(self, limit: int, offset: int | None = None):
        raise RuntimeError("Source failed")


@pytest.mark.asyncio
async def test_sourcing_step_collects_from_source():
    source = MockSource("test", [1, 2, 3, 4, 5])
    step = SourcingStep(group="test-group")
    step.add(source, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    assert len(result) == 5
    assert result.get_candidates() == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_sourcing_step_respects_limit():
    source = MockSource("test", [1, 2, 3, 4, 5])
    step = SourcingStep(group="test-group")
    step.add(source, 3)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    assert len(result) == 3
    assert result.get_candidates() == [1, 2, 3]


@pytest.mark.asyncio
async def test_sourcing_step_handles_empty_source():
    source = EmptySource()
    step = SourcingStep(group="test-group")
    step.add(source, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_sourcing_step_handles_failing_source():
    source = FailingSource()
    step = SourcingStep(group="test-group")
    step.add(source, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    # Should not raise, just return empty
    assert len(result) == 0


@pytest.mark.asyncio
async def test_sourcing_step_multiple_sources():
    source1 = MockSource("source1", [1, 2, 3])
    source2 = MockSource("source2", [4, 5, 6])
    step = SourcingStep(group="test-group")
    step.add(source1, 10)
    step.add(source2, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    assert len(result) == 6
    assert set(result.get_candidates()) == {1, 2, 3, 4, 5, 6}


@pytest.mark.asyncio
async def test_sourcing_step_no_fallback_when_sufficient_results():
    primary = MockSource("primary", [1, 2, 3, 4, 5])
    fallback = MockSource("fallback", [10, 11, 12])

    primary.fallback(fallback, threshold=0.5)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    # Primary returns 5/10 = 50%, exactly at threshold, no fallback
    assert result.get_candidates() == [1, 2, 3, 4, 5]
    assert len(fallback.collect_calls) == 0


@pytest.mark.asyncio
async def test_sourcing_step_triggers_fallback_below_threshold():
    primary = MockSource("primary", [1, 2])  # 2/10 = 20% < 50%
    fallback = MockSource("fallback", [10, 11, 12, 13, 14])

    primary.fallback(fallback, threshold=0.5)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    # Primary: 2 results, Fallback: fills remaining 8 (but only has 5)
    assert set(result.get_candidates()) == {1, 2, 10, 11, 12, 13, 14}
    assert len(fallback.collect_calls) == 1
    assert fallback.collect_calls[0]["limit"] == 8  # 10 - 2


@pytest.mark.asyncio
async def test_sourcing_step_fallback_with_custom_threshold():
    primary = MockSource("primary", [1, 2, 3])  # 3/10 = 30%
    fallback = MockSource("fallback", [10, 11, 12])

    # With 0.3 threshold, 30% is exactly at threshold, no fallback
    primary.fallback(fallback, threshold=0.3)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    assert result.get_candidates() == [1, 2, 3]
    assert len(fallback.collect_calls) == 0


@pytest.mark.asyncio
async def test_sourcing_step_fallback_triggered_at_custom_threshold():
    primary = MockSource("primary", [1, 2])  # 2/10 = 20% < 30%
    fallback = MockSource("fallback", [10, 11, 12])

    primary.fallback(fallback, threshold=0.3)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    assert set(result.get_candidates()) == {1, 2, 10, 11, 12}
    assert len(fallback.collect_calls) == 1


@pytest.mark.asyncio
async def test_sourcing_step_fallback_chain():
    primary = MockSource("primary", [1])  # 1/10 = 10%
    secondary = MockSource("secondary", [10, 11])  # 3/10 = 30%
    tertiary = MockSource("tertiary", [100, 101, 102, 103])

    primary.fallback(secondary.fallback(tertiary, threshold=0.5), threshold=0.5)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    # Chain: primary (1) -> secondary (2 more, total 3) -> tertiary (4 more, total 7)
    assert 1 in result.get_candidates()
    assert 10 in result.get_candidates()
    assert 11 in result.get_candidates()
    assert 100 in result.get_candidates()


@pytest.mark.asyncio
async def test_sourcing_step_fallback_empty_primary():
    primary = EmptySource()
    fallback = MockSource("fallback", [10, 11, 12, 13, 14, 15])

    primary.fallback(fallback, threshold=0.5)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    # Primary empty, fallback should be triggered
    assert len(result) == 6
    assert result.get_candidates() == [10, 11, 12, 13, 14, 15]


@pytest.mark.asyncio
async def test_sourcing_step_fallback_handles_failure():
    primary = MockSource("primary", [1])  # 10% < 50%
    fallback = FailingSource()

    primary.fallback(fallback, threshold=0.5)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    # Should still have primary results despite fallback failure
    assert result.get_candidates() == [1]


@pytest.mark.asyncio
async def test_sourcing_step_fallback_avoids_duplicates():
    primary = MockSource("primary", [1, 2, 3])
    fallback = MockSource("fallback", [2, 3, 4, 5, 6])  # 2, 3 are duplicates

    primary.fallback(fallback, threshold=0.5)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    # Should have 1, 2, 3 from primary and 4, 5, 6 from fallback (no duplicate 2, 3)
    assert sorted(result.get_candidates()) == [1, 2, 3, 4, 5, 6]


@pytest.mark.asyncio
async def test_sourcing_step_source_without_fallback():
    source = MockSource("source", [1, 2])  # 20% < 50% but no fallback

    step = SourcingStep(group="test-group")
    step.add(source, 10)

    candidates = CandidateList("status_id")
    result = await step(candidates)

    # No fallback configured, just return what we have
    assert result.get_candidates() == [1, 2]


@pytest.mark.asyncio
async def test_sourcing_step_records_duration_with_fallback():
    primary = MockSource("primary", [1])
    fallback = MockSource("fallback", [10, 11, 12])

    primary.fallback(fallback, threshold=0.5)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    await step(candidates)

    # Duration should include both primary and fallback collection
    durations = step.get_durations()
    assert len(durations) == 1
    assert durations[0] > 0


@pytest.mark.asyncio
async def test_sourcing_step_records_count_with_fallback():
    primary = MockSource("primary", [1])
    fallback = MockSource("fallback", [10, 11, 12])

    primary.fallback(fallback, threshold=0.5)

    step = SourcingStep(group="test-group")
    step.add(primary, 10)

    candidates = CandidateList("status_id")
    await step(candidates)

    # Count should include both primary and fallback
    counts = step.get_counts()
    assert counts[0] == 4


@pytest.mark.asyncio
async def test_fallback_step_no_action_when_sufficient():
    fallback_source = MockSource("fallback", [100, 101, 102])

    step = FallbackStep(fallback_source, target=5)

    # Already have 5 candidates
    candidates = CandidateList("status_id")
    for i in range(5):
        candidates.append(i, source="primary", source_group="primary")

    result = await step(candidates)

    assert len(result) == 5
    assert step.get_filled_count() == 0
    assert len(fallback_source.collect_calls) == 0


@pytest.mark.asyncio
async def test_fallback_step_fills_gap():
    fallback_source = MockSource("fallback", [100, 101, 102, 103, 104])

    step = FallbackStep(fallback_source, target=5)

    # Only have 2 candidates
    candidates = CandidateList("status_id")
    candidates.append(1, source="primary", source_group="primary")
    candidates.append(2, source="primary", source_group="primary")

    result = await step(candidates)

    assert len(result) == 5
    assert step.get_filled_count() == 3
    assert 100 in result.get_candidates()
    assert 101 in result.get_candidates()
    assert 102 in result.get_candidates()


@pytest.mark.asyncio
async def test_fallback_step_fills_empty_feed():
    fallback_source = MockSource("fallback", [100, 101, 102, 103, 104])

    step = FallbackStep(fallback_source, target=5)

    # Empty feed
    candidates = CandidateList("status_id")

    result = await step(candidates)

    assert len(result) == 5
    assert step.get_filled_count() == 5


@pytest.mark.asyncio
async def test_fallback_step_avoids_duplicates():
    fallback_source = MockSource("fallback", [1, 2, 100, 101, 102])  # 1, 2 are duplicates

    step = FallbackStep(fallback_source, target=5)

    # Already have 1, 2
    candidates = CandidateList("status_id")
    candidates.append(1, source="primary", source_group="primary")
    candidates.append(2, source="primary", source_group="primary")

    result = await step(candidates)

    assert len(result) == 5
    # Should have 1, 2 from primary and 100, 101, 102 from fallback (no duplicate 1, 2)
    assert sorted(result.get_candidates()) == [1, 2, 100, 101, 102]


@pytest.mark.asyncio
async def test_fallback_step_handles_insufficient_fallback():
    fallback_source = MockSource("fallback", [100, 101])  # Only 2 available

    step = FallbackStep(fallback_source, target=10)

    candidates = CandidateList("status_id")
    candidates.append(1, source="primary", source_group="primary")

    result = await step(candidates)

    # Can only fill with 2 from fallback
    assert len(result) == 3
    assert step.get_filled_count() == 2


@pytest.mark.asyncio
async def test_fallback_step_handles_failing_source():
    fallback_source = FailingSource()

    step = FallbackStep(fallback_source, target=10)

    candidates = CandidateList("status_id")
    candidates.append(1, source="primary", source_group="primary")

    result = await step(candidates)

    # Should not crash, just keep existing candidates
    assert len(result) == 1
    assert step.get_filled_count() == 0


@pytest.mark.asyncio
async def test_fallback_step_sets_correct_source_group():
    fallback_source = MockSource("trending", [100, 101])

    step = FallbackStep(fallback_source, target=5, group="my-fallback-group")

    candidates = CandidateList("status_id")
    candidates.append(1, source="primary", source_group="primary")

    result = await step(candidates)

    # Check that fallback candidates have correct source group
    sources_100 = result.get_source(100)
    sources_101 = result.get_source(101)

    assert any(group == "my-fallback-group" for _, group in sources_100)
    assert any(group == "my-fallback-group" for _, group in sources_101)


@pytest.mark.asyncio
async def test_fallback_step_records_duration():
    fallback_source = MockSource("fallback", [100, 101, 102])

    step = FallbackStep(fallback_source, target=5)

    candidates = CandidateList("status_id")
    candidates.append(1, source="primary", source_group="primary")

    await step(candidates)

    assert step.get_duration() > 0


@pytest.mark.asyncio
async def test_fallback_step_get_params():
    fallback_source = MockSource("trending", [100])

    step = FallbackStep(fallback_source, target=20, group="fallback")

    params = step.get_params()

    assert params["source"] == "mock_source"
    assert params["target"] == 20
    assert params["group"] == "fallback"
