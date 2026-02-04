import math
import sys
from datetime import UTC, datetime, timedelta, timezone
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def _import_without_init(module_path: str, module_name: str):
    """Import a module directly without going through __init__.py."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)

    # We need to mock the parent packages for relative imports
    parent_name = "modules.fediway.sources"
    if parent_name not in sys.modules:
        # Create stub parent modules
        for i, part in enumerate(parent_name.split(".")):
            full_name = ".".join(parent_name.split(".")[:i+1])
            if full_name not in sys.modules:
                sys.modules[full_name] = ModuleType(full_name)

    # Import base first
    base_spec = importlib.util.spec_from_file_location(
        "modules.fediway.sources.base",
        "modules/fediway/sources/base.py"
    )
    base_module = importlib.util.module_from_spec(base_spec)
    sys.modules["modules.fediway.sources.base"] = base_module
    base_spec.loader.exec_module(base_module)

    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_module = _import_without_init(
    "modules/fediway/sources/statuses/follows_engaging_now.py",
    "modules.fediway.sources.statuses.follows_engaging_now"
)
FollowsEngagingNowSource = _module.FollowsEngagingNowSource


def utcnow():
    return datetime.now(timezone.utc)


def test_source_id():
    mock_rw = MagicMock()
    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1)
    assert source.id == "follows_engaging_now"


def test_source_tracked_params():
    mock_rw = MagicMock()
    source = FollowsEngagingNowSource(
        rw=mock_rw,
        account_id=1,
        min_engaged_follows=2,
        max_per_author=3,
    )
    params = source.get_params()
    assert params == {"min_engaged_follows": 2, "max_per_author": 3}


def test_collect_empty_results():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result == []


def test_collect_returns_status_ids():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)
    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 3, now - timedelta(hours=1), 5.0),
        (102, 202, 2, now - timedelta(hours=2), 3.0),
    ]

    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert 101 in result
    assert 102 in result


def test_scoring_favors_more_engaged_follows():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)
    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 5, now, 1.0),  # 5 follows engaged
        (102, 202, 1, now, 1.0),  # 1 follow engaged
    ]

    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 101


def test_scoring_favors_recent_engagements():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)
    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 2, now - timedelta(hours=4), 1.0),  # older
        (102, 202, 2, now - timedelta(minutes=30), 1.0),  # fresher
    ]

    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 102


def test_scoring_favors_higher_engagement_weight():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)
    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 2, now, 10.0),  # high weight (reblogs/replies)
        (102, 202, 2, now, 1.0),   # low weight (just favs)
    ]

    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 101


def test_diversity_limits_per_author():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)
    # Same author (201) has 4 posts
    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 5, now, 1.0),
        (102, 201, 4, now, 1.0),
        (103, 201, 3, now, 1.0),
        (104, 201, 2, now, 1.0),
        (105, 202, 1, now, 1.0),  # different author
    ]

    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1, max_per_author=2)
    result = source.collect(10)

    author_201_count = sum(1 for sid in result if sid in [101, 102, 103, 104])
    assert author_201_count == 2
    assert 105 in result


def test_diversity_allows_multiple_authors():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)
    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 3, now, 1.0),
        (102, 202, 3, now, 1.0),
        (103, 203, 3, now, 1.0),
        (104, 201, 2, now, 1.0),
        (105, 202, 2, now, 1.0),
    ]

    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1, max_per_author=2)
    result = source.collect(10)

    assert len(result) == 5


def test_respects_limit():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)
    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 5, now, 1.0),
        (102, 202, 4, now, 1.0),
        (103, 203, 3, now, 1.0),
        (104, 204, 2, now, 1.0),
        (105, 205, 1, now, 1.0),
    ]

    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1)
    result = source.collect(3)

    assert len(result) == 3


def test_query_uses_correct_parameters():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = FollowsEngagingNowSource(
        rw=mock_rw,
        account_id=42,
        min_engaged_follows=3,
    )
    source.collect(10)

    call_args = mock_rw.execute.call_args
    params = call_args[0][1]
    assert params["user_id"] == 42
    assert params["min_follows"] == 3
    assert params["limit"] == 50  # limit * 5


def test_score_formula():
    mock_rw = MagicMock()
    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1)

    now = datetime.now(UTC).replace(tzinfo=None)
    candidates = [
        (100, 200, 3, now - timedelta(hours=2), 5.0),
    ]

    scored = source._score_candidates(candidates)

    # social_proof = 3 ** 1.5 = 5.196...
    # recency_boost = 0.5 ** (2 / 2) = 0.5
    # type_weight = log(1 + 5) = 1.791...
    # score = 5.196 * 0.5 * 1.791 = 4.65...
    expected_social = 3 ** 1.5
    expected_recency = 0.5  # 2h with 2h half-life
    expected_type = math.log(1 + 5.0)
    expected_score = expected_social * expected_recency * expected_type

    assert abs(scored[0]["score"] - expected_score) < 0.1


def test_handles_large_network():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    # Simulate 500 candidates from many authors
    candidates = [
        (1000 + i, 2000 + (i % 100), 5 - (i % 5), now - timedelta(minutes=i), 1.0 + (i % 3))
        for i in range(500)
    ]
    mock_rw.execute.return_value.fetchall.return_value = candidates

    source = FollowsEngagingNowSource(rw=mock_rw, account_id=1, max_per_author=2)
    result = source.collect(50)

    assert len(result) == 50


def test_min_engaged_follows_filters():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = FollowsEngagingNowSource(
        rw=mock_rw,
        account_id=1,
        min_engaged_follows=5,
    )
    source.collect(10)

    call_args = mock_rw.execute.call_args
    params = call_args[0][1]
    assert params["min_follows"] == 5
