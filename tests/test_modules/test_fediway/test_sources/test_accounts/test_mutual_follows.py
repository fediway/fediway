from unittest.mock import MagicMock

from modules.fediway.sources.accounts import MutualFollowsSource


def test_mutual_follows_source_has_required_attributes():
    mock_rw = MagicMock()
    source = MutualFollowsSource(rw=mock_rw, account_id=1)

    assert source.id == "mutual_follows"
    assert "min_mutual_follows" in source._tracked_params


def test_mutual_follows_source_get_params():
    mock_rw = MagicMock()
    source = MutualFollowsSource(
        rw=mock_rw,
        account_id=1,
        min_mutual_follows=5,
        exclude_following=False,
    )

    params = source.get_params()

    assert params["min_mutual_follows"] == 5
    assert params["exclude_following"] is False


def test_mutual_follows_source_collect_executes_query():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = [
        (100, 5),
        (200, 3),
        (300, 2),
    ]

    source = MutualFollowsSource(rw=mock_rw, account_id=1, min_mutual_follows=2)
    results = source.collect(limit=10)

    assert results == [100, 200, 300]
    mock_rw.execute.assert_called_once()


def test_mutual_follows_source_collect_returns_empty_on_no_results():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = MutualFollowsSource(rw=mock_rw, account_id=1)
    results = source.collect(limit=10)

    assert results == []


def test_mutual_follows_source_respects_limit():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = [(100, 5)]

    source = MutualFollowsSource(rw=mock_rw, account_id=1)
    source.collect(limit=20)

    call_args = mock_rw.execute.call_args
    assert call_args[0][1]["limit"] == 20
