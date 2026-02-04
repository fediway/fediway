import math
import sys
from datetime import UTC, datetime, timedelta
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def _import_without_init(module_path: str, module_name: str):
    import importlib.util

    parent_name = "modules.fediway.sources"
    if parent_name not in sys.modules:
        for i, part in enumerate(parent_name.split(".")):
            full_name = ".".join(parent_name.split(".")[:i+1])
            if full_name not in sys.modules:
                sys.modules[full_name] = ModuleType(full_name)

    base_spec = importlib.util.spec_from_file_location(
        "modules.fediway.sources.base",
        "modules/fediway/sources/base.py"
    )
    base_module = importlib.util.module_from_spec(base_spec)
    sys.modules["modules.fediway.sources.base"] = base_module
    base_spec.loader.exec_module(base_module)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_module = _import_without_init(
    "modules/fediway/sources/statuses/smart_follows.py",
    "modules.fediway.sources.statuses.smart_follows"
)
SmartFollowsSource = _module.SmartFollowsSource


def test_source_id():
    mock_rw = MagicMock()
    source = SmartFollowsSource(rw=mock_rw, account_id=1)
    assert source.id == "smart_follows"


def test_source_tracked_params():
    mock_rw = MagicMock()
    source = SmartFollowsSource(
        rw=mock_rw,
        account_id=1,
        recency_half_life_hours=6,
        max_age_hours=24,
        max_per_author=2,
        volume_threshold=10,
    )
    params = source.get_params()
    assert params == {
        "recency_half_life_hours": 6,
        "max_age_hours": 24,
        "max_per_author": 2,
        "volume_threshold": 10,
    }


def test_collect_empty_affinities():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = SmartFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result == []


def test_collect_returns_status_ids():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_followed_affinity" in query_str:
            mock_result.fetchall.return_value = [
                (201, 5.0, 0.0, 5.0, "direct"),
                (202, 3.0, 0.0, 3.0, "direct"),
            ]
        elif "statuses" in query_str:
            mock_result.fetchall.return_value = [
                (101, 201, now - timedelta(hours=1), 2),
                (102, 202, now - timedelta(hours=2), 1),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SmartFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert 101 in result
    assert 102 in result


def test_scoring_favors_high_affinity():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_followed_affinity" in query_str:
            mock_result.fetchall.return_value = [
                (201, 50.0, 0.0, 50.0, "direct"),
                (202, 1.0, 0.0, 1.0, "direct"),
            ]
        elif "statuses" in query_str:
            mock_result.fetchall.return_value = [
                (101, 201, now, 1),
                (102, 202, now, 1),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SmartFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 101


def test_scoring_favors_recent_posts():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_followed_affinity" in query_str:
            mock_result.fetchall.return_value = [
                (201, 5.0, 0.0, 5.0, "direct"),
            ]
        elif "statuses" in query_str:
            mock_result.fetchall.return_value = [
                (101, 201, now - timedelta(hours=24), 1),
                (102, 201, now - timedelta(hours=1), 1),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SmartFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 102


def test_volume_penalty_applied():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_followed_affinity" in query_str:
            mock_result.fetchall.return_value = [
                (201, 5.0, 0.0, 5.0, "direct"),
                (202, 5.0, 0.0, 5.0, "direct"),
            ]
        elif "statuses" in query_str:
            mock_result.fetchall.return_value = [
                (101, 201, now, 50),  # high volume author
                (102, 202, now, 1),   # low volume author
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SmartFollowsSource(rw=mock_rw, account_id=1, volume_threshold=5)
    result = source.collect(10)

    # Low volume should rank higher due to no penalty
    assert result[0] == 102


def test_diversity_limits_per_author():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_followed_affinity" in query_str:
            mock_result.fetchall.return_value = [
                (201, 10.0, 0.0, 10.0, "direct"),
                (202, 5.0, 0.0, 5.0, "direct"),
            ]
        elif "statuses" in query_str:
            mock_result.fetchall.return_value = [
                (101, 201, now, 1),
                (102, 201, now - timedelta(minutes=1), 1),
                (103, 201, now - timedelta(minutes=2), 1),
                (104, 201, now - timedelta(minutes=3), 1),
                (105, 202, now - timedelta(minutes=4), 1),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SmartFollowsSource(rw=mock_rw, account_id=1, max_per_author=2)
    result = source.collect(10)

    author_201_count = sum(1 for sid in result if sid in [101, 102, 103, 104])
    assert author_201_count == 2
    assert 105 in result


def test_cold_start_equal_weights():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_followed_affinity" in query_str:
            # No affinity data (cold start)
            mock_result.fetchall.return_value = []
        elif "statuses" in query_str:
            mock_result.fetchall.return_value = [
                (101, 201, now, 1),
                (102, 202, now, 1),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SmartFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    # Both should be included with equal weight
    assert len(result) == 2


def test_inferred_affinity_used():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_followed_affinity" in query_str:
            mock_result.fetchall.return_value = [
                (201, 0.0, 10.0, 7.0, "inferred"),  # 10 * 0.7 = 7
                (202, 5.0, 0.0, 5.0, "direct"),
            ]
        elif "statuses" in query_str:
            mock_result.fetchall.return_value = [
                (101, 201, now, 1),
                (102, 202, now, 1),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SmartFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    # Author 201 with inferred affinity 7.0 should rank higher than 202 with 5.0
    assert result[0] == 101


def test_respects_limit():
    mock_rw = MagicMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_followed_affinity" in query_str:
            mock_result.fetchall.return_value = [
                (200 + i, 10.0 - i, 0.0, 10.0 - i, "direct")
                for i in range(10)
            ]
        elif "statuses" in query_str:
            mock_result.fetchall.return_value = [
                (100 + i, 200 + i, now - timedelta(minutes=i), 1)
                for i in range(10)
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SmartFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(5)

    assert len(result) == 5
