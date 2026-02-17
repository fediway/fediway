from unittest.mock import MagicMock

from apps.api.sources.accounts import PopularAccountsSource


def test_popular_accounts_source_has_required_attributes():
    mock_rw = MagicMock()
    source = PopularAccountsSource(rw=mock_rw, account_id=1)

    assert source.id == "popular_accounts"
    assert "min_followers" in source._tracked_params
    assert "local_only" in source._tracked_params


def test_popular_accounts_source_get_params():
    mock_rw = MagicMock()
    source = PopularAccountsSource(
        rw=mock_rw,
        account_id=1,
        min_followers=100,
        local_only=False,
    )

    params = source.get_params()

    assert params["min_followers"] == 100
    assert params["local_only"] is False


def test_popular_accounts_source_collect_returns_ids():
    mock_rw = MagicMock()

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "popular_accounts" in query_str:
            mock_result.fetchall.return_value = [
                (100, 500),
                (200, 300),
            ]
        elif "follows" in query_str:
            mock_result.fetchall.return_value = []
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = PopularAccountsSource(rw=mock_rw, account_id=1)
    results = source.collect(limit=10)

    assert results == [100, 200]


def test_popular_accounts_source_excludes_followed():
    mock_rw = MagicMock()

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "popular_accounts" in query_str:
            mock_result.fetchall.return_value = [
                (100, 500),
                (200, 300),
            ]
        elif "follows" in query_str:
            mock_result.fetchall.return_value = [(100,)]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = PopularAccountsSource(rw=mock_rw, account_id=1)
    results = source.collect(limit=10)

    assert 100 not in results
    assert 200 in results


def test_popular_accounts_source_includes_followed_when_disabled():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = [
        (100, 500),
        (200, 300),
    ]

    source = PopularAccountsSource(rw=mock_rw, account_id=1, exclude_following=False)
    results = source.collect(limit=10)

    assert results == [100, 200]
