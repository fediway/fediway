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
    "modules/fediway/sources/statuses/posted_by_friends_of_friends.py",
    "modules.fediway.sources.statuses.posted_by_friends_of_friends",
)
PostedByFriendsOfFriendsSource = _module.PostedByFriendsOfFriendsSource


def test_source_id():
    mock_rw = MagicMock()
    source = PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=1)
    assert source.id == "posted_by_friends_of_friends"


def test_source_tracked_params():
    mock_rw = MagicMock()
    source = PostedByFriendsOfFriendsSource(
        rw=mock_rw,
        account_id=1,
        min_mutual_follows=5,
        max_per_author=3,
    )
    params = source.get_params()
    assert params == {"min_mutual_follows": 5, "max_per_author": 3}


def test_collect_empty():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result == []


def test_collect_returns_status_ids():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 5, now),  # status_id, author_id, followed_by_count, created_at
        (102, 202, 3, now),
    ]

    source = PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert 101 in result
    assert 102 in result


def test_scoring_favors_more_mutual_follows():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 10, now),
        (102, 202, 3, now),
    ]

    source = PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 101


def test_scoring_favors_recent_posts():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 5, now - timedelta(hours=24)),
        (102, 202, 5, now),
    ]

    source = PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 102


def test_diversity_limits_per_author():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 10, now),
        (102, 201, 9, now - timedelta(minutes=1)),
        (103, 201, 8, now - timedelta(minutes=2)),
        (104, 202, 7, now - timedelta(minutes=3)),
    ]

    source = PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=1, max_per_author=2)
    result = source.collect(10)

    author_201_count = sum(1 for sid in result if sid in [101, 102, 103])
    assert author_201_count == 2
    assert 104 in result


def test_respects_limit():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.return_value.fetchall.return_value = [
        (100 + i, 200 + i, 10 - i, now - timedelta(minutes=i)) for i in range(10)
    ]

    source = PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=1)
    result = source.collect(5)

    assert len(result) == 5


def test_query_uses_min_mutual_follows():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=42, min_mutual_follows=7)
    source.collect(10)

    call_args = mock_rw.execute.call_args
    params = call_args[0][1]
    assert params["user_id"] == 42
    assert params["min_mutual"] == 7
