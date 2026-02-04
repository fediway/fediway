import sys
from datetime import datetime, timedelta, timezone
from types import ModuleType
from unittest.mock import MagicMock


def _import_without_init(module_path: str, module_name: str):
    import importlib.util

    parent_name = "modules.fediway.sources"
    if parent_name not in sys.modules:
        for i, part in enumerate(parent_name.split(".")):
            full_name = ".".join(parent_name.split(".")[: i + 1])
            if full_name not in sys.modules:
                sys.modules[full_name] = ModuleType(full_name)

    base_spec = importlib.util.spec_from_file_location(
        "modules.fediway.sources.base", "modules/fediway/sources/base.py"
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
    "modules/fediway/sources/statuses/tag_affinity.py",
    "modules.fediway.sources.statuses.tag_affinity",
)
TagAffinitySource = _module.TagAffinitySource


def test_source_id():
    mock_rw = MagicMock()
    source = TagAffinitySource(rw=mock_rw, account_id=1)
    assert source.id == "tag_affinity"


def test_source_tracked_params():
    mock_rw = MagicMock()
    source = TagAffinitySource(
        rw=mock_rw,
        account_id=1,
        max_age_hours=24,
        max_per_tag=3,
        max_per_author=1,
        in_network_penalty=0.3,
    )
    params = source.get_params()
    assert params == {
        "max_age_hours": 24,
        "max_per_tag": 3,
        "max_per_author": 1,
        "in_network_penalty": 0.3,
    }


def test_collect_empty_affinities():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = TagAffinitySource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result == []


def test_collect_returns_status_ids():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_top_tags" in query_str:
            mock_result.fetchall.return_value = [
                (1001, 10.0),  # tag_id, raw_affinity
                (1002, 5.0),
            ]
        elif "user_inferred_tag_affinity" in query_str:
            mock_result.fetchall.return_value = []
        elif "follows" in query_str:
            mock_result.fetchall.return_value = []
        elif "tag_recent_statuses" in query_str:
            mock_result.fetchall.return_value = [
                (1001, 101, 201, now),  # tag_id, status_id, author_id, created_at
                (1002, 102, 202, now),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = TagAffinitySource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert 101 in result
    assert 102 in result


def test_in_network_penalty_applied():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_top_tags" in query_str:
            mock_result.fetchall.return_value = [(1001, 10.0)]
        elif "user_inferred_tag_affinity" in query_str:
            mock_result.fetchall.return_value = []
        elif "follows" in query_str:
            mock_result.fetchall.return_value = [(201,)]  # author 201 is followed
        elif "tag_recent_statuses" in query_str:
            mock_result.fetchall.return_value = [
                (1001, 101, 201, now),  # followed author
                (1001, 102, 202, now),  # not followed
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = TagAffinitySource(rw=mock_rw, account_id=1, in_network_penalty=0.5)
    result = source.collect(10)

    # Not-followed author should rank higher due to no penalty
    assert result[0] == 102


def test_diversity_limits_per_tag():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_top_tags" in query_str:
            mock_result.fetchall.return_value = [(1001, 10.0), (1002, 5.0)]
        elif "user_inferred_tag_affinity" in query_str:
            mock_result.fetchall.return_value = []
        elif "follows" in query_str:
            mock_result.fetchall.return_value = []
        elif "tag_recent_statuses" in query_str:
            mock_result.fetchall.return_value = [
                (1001, 101, 201, now),
                (1001, 102, 202, now - timedelta(minutes=1)),
                (1001, 103, 203, now - timedelta(minutes=2)),
                (1002, 104, 204, now - timedelta(minutes=3)),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = TagAffinitySource(rw=mock_rw, account_id=1, max_per_tag=2)
    result = source.collect(10)

    tag_1001_count = sum(1 for sid in result if sid in [101, 102, 103])
    assert tag_1001_count == 2
    assert 104 in result


def test_diversity_limits_per_author():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_top_tags" in query_str:
            mock_result.fetchall.return_value = [(1001, 10.0)]
        elif "user_inferred_tag_affinity" in query_str:
            mock_result.fetchall.return_value = []
        elif "follows" in query_str:
            mock_result.fetchall.return_value = []
        elif "tag_recent_statuses" in query_str:
            mock_result.fetchall.return_value = [
                (1001, 101, 201, now),
                (1001, 102, 201, now - timedelta(minutes=1)),
                (1001, 103, 201, now - timedelta(minutes=2)),
                (1001, 104, 202, now - timedelta(minutes=3)),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = TagAffinitySource(rw=mock_rw, account_id=1, max_per_author=2, max_per_tag=10)
    result = source.collect(10)

    author_201_count = sum(1 for sid in result if sid in [101, 102, 103])
    assert author_201_count == 2
    assert 104 in result


def test_inferred_affinity_used_as_fallback():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_top_tags" in query_str:
            mock_result.fetchall.return_value = []  # no direct affinity
        elif "user_inferred_tag_affinity" in query_str:
            mock_result.fetchall.return_value = [(1001, 10.0)]  # inferred
        elif "follows" in query_str:
            mock_result.fetchall.return_value = []
        elif "tag_recent_statuses" in query_str:
            mock_result.fetchall.return_value = [
                (1001, 101, 201, now),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = TagAffinitySource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert 101 in result


def test_direct_affinity_overrides_inferred():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_top_tags" in query_str:
            mock_result.fetchall.return_value = [(1001, 20.0)]  # direct
        elif "user_inferred_tag_affinity" in query_str:
            mock_result.fetchall.return_value = [(1001, 5.0)]  # inferred (lower, should be ignored)
        elif "follows" in query_str:
            mock_result.fetchall.return_value = []
        elif "tag_recent_statuses" in query_str:
            mock_result.fetchall.return_value = [
                (1001, 101, 201, now),
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = TagAffinitySource(rw=mock_rw, account_id=1)

    # Should use direct affinity (20.0) not inferred (5.0 * 0.7)
    tag_affinities = source._get_tag_affinities()
    inferred = source._get_inferred_tag_affinities()

    assert tag_affinities[1001] == 20.0
    assert inferred[1001] == 5.0 * 0.7


def test_respects_limit():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_top_tags" in query_str:
            mock_result.fetchall.return_value = [(1001, 10.0)]
        elif "user_inferred_tag_affinity" in query_str:
            mock_result.fetchall.return_value = []
        elif "follows" in query_str:
            mock_result.fetchall.return_value = []
        elif "tag_recent_statuses" in query_str:
            mock_result.fetchall.return_value = [
                (1001, 100 + i, 200 + i, now - timedelta(minutes=i)) for i in range(10)
            ]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = TagAffinitySource(rw=mock_rw, account_id=1, max_per_tag=20, max_per_author=20)
    result = source.collect(5)

    assert len(result) == 5
