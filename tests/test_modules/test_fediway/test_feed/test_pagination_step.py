import numpy as np
import pytest

from modules.fediway.feed import CandidateList
from modules.fediway.feed.steps import PaginationStep


@pytest.fixture
def sample_candidates():
    candidates = CandidateList("status_id")

    # Add some sample status IDs with scores and sources
    candidates.append(101, 0.9, "collaborative_filtering", "out_network")
    candidates.append(102, 0.8, "trending_feed", "trending")
    candidates.append(103, 0.7, "collaborative_filtering", "out_network")
    candidates.append(104, 0.6, "user_follows", "following_activity")
    candidates.append(105, 0.5, "trending_hashtag", "trending")
    candidates.append(106, 0.4, "search_results", "search")
    candidates.append(107, 0.3, "ads_feed", "promoted_content")
    candidates.append(108, 0.2, "timeline_feed", "user_timeline")
    candidates.append(109, 0.1, "trending_feed", "trending")
    candidates.append(110, 0.05, "collaborative_filtering", "out_network")

    return candidates


@pytest.fixture
def empty_candidate_list():
    return CandidateList("status_id")


def test_pagination_step_init():
    step = PaginationStep("status_id", limit=5)

    assert step.candidates.entity == "status_id"
    assert step.limit == 5
    assert step.offset == 0
    assert step.max_id is None
    assert len(step.candidates) == 0


def test_pagination_step_init_with_offset():
    step = PaginationStep("account_id", limit=10, offset=5)

    assert step.limit == 10
    assert step.offset == 5
    assert step.max_id is None


def test_pagination_step_init_with_max_id():
    step = PaginationStep("status_id", limit=3, max_id=100)

    assert step.limit == 3
    assert step.offset == 0
    assert step.max_id == 100


def test_get_params():
    step = PaginationStep("status_id", limit=5, offset=2, max_id=99)

    assert step.get_params() == {"limit": 5, "offset": 2, "max_id": 99}


def test_get_params_defaults():
    step = PaginationStep("account_id", limit=10)

    assert step.get_params() == {"limit": 10, "offset": 0, "max_id": None}


def test_get_state_empty():
    step = PaginationStep("status_id", limit=5)
    state = step.get_state()

    assert "candidates" in state
    assert state["candidates"]["ids"] == []
    assert state["candidates"]["scores"] == []
    assert state["candidates"]["sources"] == {}


def test_get_set_state_with_data(sample_candidates):
    step = PaginationStep("status_id", limit=5)

    step.candidates = sample_candidates

    # Get state
    state = step.get_state()

    # Create new step and set state
    new_step = PaginationStep("status_id", limit=5)
    new_step.set_state(state)

    # Verify state was restored correctly
    assert len(new_step.candidates) == len(sample_candidates)
    assert new_step.candidates.get_candidates() == sample_candidates.get_candidates()
    np.testing.assert_array_equal(new_step.candidates.get_scores(), sample_candidates.get_scores())


def test_set_state_invalid():
    step = PaginationStep("status_id", limit=5)
    initial_len = len(step.candidates)

    # Should not raise error and should not change candidates
    step.set_state({"other_key": "value"})

    assert len(step.candidates) == initial_len


def test_results_with_offset(sample_candidates):
    step = PaginationStep("status_id", limit=3, offset=2)
    step.candidates = sample_candidates

    results = step.results()

    assert len(results) == 3
    assert results.get_candidates() == [103, 104, 105]
    np.testing.assert_array_almost_equal(results.get_scores(), [0.7, 0.6, 0.5])


def test_results_with_offset_beyond_data(sample_candidates):
    step = PaginationStep("status_id", limit=5, offset=15)
    step.candidates = sample_candidates

    results = step.results()

    assert len(results) == 0
    assert results.get_candidates() == []


def test_results_with_offset_partial_page(sample_candidates):
    step = PaginationStep("status_id", limit=5, offset=8)
    step.candidates = sample_candidates

    results = step.results()

    assert len(results) == 2  # Only 2 items left after offset 8
    assert results.get_candidates() == [109, 110]


def test_results_with_max_id(sample_candidates):
    step = PaginationStep("status_id", limit=3, max_id=104)
    step.candidates = sample_candidates

    results = step.results()

    assert len(results) == 3

    # Should start after id 104
    assert results.get_candidates() == [105, 106, 107]


def test_results_with_max_id_at_end(sample_candidates):
    step = PaginationStep("status_id", limit=5, max_id=108)
    step.candidates = sample_candidates

    results = step.results()

    assert len(results) == 2  # Only 2 items left after max_id 108
    assert results.get_candidates() == [109, 110]


def test_results_from_beginning(sample_candidates):
    step = PaginationStep("status_id", limit=4)
    step.candidates = sample_candidates

    results = step.results()

    assert len(results) == 4
    assert results.get_candidates() == [101, 102, 103, 104]
    np.testing.assert_array_almost_equal(results.get_scores(), [0.9, 0.8, 0.7, 0.6])


def test_results_limit_larger_than_data(sample_candidates):
    step = PaginationStep("status_id", limit=20)
    step.candidates = sample_candidates

    results = step.results()

    assert len(results) == 10  # All available data
    assert results.get_candidates() == sample_candidates.get_candidates()


def test_len_empty():
    step = PaginationStep("status_id", limit=5)

    assert len(step) == 0


def test_len_with_data(sample_candidates):
    step = PaginationStep("status_id", limit=5)
    step.candidates = sample_candidates
    assert len(step) == 10


@pytest.mark.asyncio
async def test_call_method_empty():
    step = PaginationStep("status_id", limit=3)

    new_candidates = CandidateList("status_id")
    new_candidates.append(201, 0.9, "new_feed", "new_source")
    new_candidates.append(202, 0.8, "new_feed", "new_source")
    new_candidates.append(203, 0.7, "new_feed", "new_source")
    new_candidates.append(204, 0.6, "new_feed", "new_source")

    results = await step(new_candidates)

    # Should have added all candidates and returned first 3
    assert len(step.candidates) == 4
    assert len(results) == 3
    assert results.get_candidates() == [201, 202, 203]


@pytest.mark.asyncio
async def test_call_method_with_existing_data(sample_candidates):
    step = PaginationStep("status_id", limit=5, offset=2)
    step.candidates = sample_candidates

    new_candidates = CandidateList("status_id")
    new_candidates.append(201, 0.95, "new_feed", "new_source")
    new_candidates.append(202, 0.85, "new_feed", "new_source")

    results = await step(new_candidates)

    # Should have added new candidates to existing ones
    assert len(step.candidates) == 12  # 10 original + 2 new
    assert len(results) == 5  # limit=5 starting from offset=2

    # Results should start from offset 2 of combined candidates
    expected_candidates = [103, 104, 105, 106, 107]
    assert results.get_candidates() == expected_candidates


@pytest.mark.asyncio
async def test_call_method_with_max_id(sample_candidates):
    step = PaginationStep("status_id", limit=3, max_id=105)
    step.candidates = sample_candidates

    new_candidates = CandidateList("status_id")
    new_candidates.append(201, 0.4, "new_feed", "new_source")

    results = await step(new_candidates)

    assert len(results) == 3
    assert results.get_candidates() == [106, 107, 108]


def test_zero_limit():
    step = PaginationStep("status_id", limit=0)

    candidates = CandidateList("status_id")
    candidates.append(101, 0.9, "test", "test")
    step.candidates = candidates

    results = step.results()
    assert len(results) == 0


def test_negative_offset():
    step = PaginationStep("status_id", limit=3, offset=-5)

    candidates = CandidateList("status_id")
    candidates.append(101, 0.9, "test", "test")
    candidates.append(102, 0.8, "test", "test")
    step.candidates = candidates

    results = step.results()

    # With offset=-5, it should still start from beginning
    assert len(results) == 2
    assert results.get_candidates() == [101, 102]


def test_different_entity_types():
    step = PaginationStep("domain", limit=2)
    candidates = CandidateList("domain")
    candidates.append("mastodon.social", 0.9, "engaged_instances", "instance")
    candidates.append("chaos.social", 0.8, "engaged_instances", "instances")
    step.candidates = candidates

    results = step.results()
    assert len(results) == 2
    assert results.get_candidates() == ["mastodon.social", "chaos.social"]


@pytest.mark.asyncio
async def test_multiple_calls():
    step = PaginationStep("status_id", limit=3)

    # First call
    candidates1 = CandidateList("status_id")
    candidates1.append(101, 0.9, "feed1", "source1")
    candidates1.append(102, 0.8, "feed1", "source1")

    results1 = await step(candidates1)
    assert len(results1) == 2
    assert len(step.candidates) == 2

    # Second call - should accumulate
    candidates2 = CandidateList("status_id")
    candidates2.append(103, 0.7, "feed2", "source2")
    candidates2.append(104, 0.6, "feed2", "source2")

    results2 = await step(candidates2)
    assert len(results2) == 3  # limit=3
    assert len(step.candidates) == 4  # total accumulated
    assert results2.get_candidates() == [101, 102, 103]


def test_source_preservation_in_results(sample_candidates):
    step = PaginationStep("status_id", limit=2, offset=1)
    step.candidates = sample_candidates

    results = step.results()

    # Check that sources are preserved
    assert len(results) == 2
    candidate_102 = results[0]  # This should be candidate 102
    candidate_103 = results[1]  # This should be candidate 103

    assert candidate_102.id == 102
    assert candidate_103.id == 103

    # Verify sources are maintained
    sources_102 = results.get_source(102)
    sources_103 = results.get_source(103)

    assert len(sources_102) > 0
    assert len(sources_103) > 0
