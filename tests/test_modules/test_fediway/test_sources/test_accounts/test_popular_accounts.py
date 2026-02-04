from unittest.mock import MagicMock

from modules.fediway.sources.accounts import PopularAccountsSource


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


def test_popular_accounts_source_collect_executes_query():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = [
        (100, 500),
        (200, 300),
    ]

    source = PopularAccountsSource(rw=mock_rw, account_id=1)
    results = source.collect(limit=10)

    assert results == [100, 200]
    mock_rw.execute.assert_called_once()


def test_popular_accounts_source_passes_config_to_query():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = PopularAccountsSource(
        rw=mock_rw,
        account_id=42,
        min_followers=50,
        local_only=True,
        min_account_age_days=14,
    )
    source.collect(limit=25)

    call_args = mock_rw.execute.call_args[0][1]
    assert call_args["account_id"] == 42
    assert call_args["min_followers"] == 50
    assert call_args["local_only"] is True
    assert call_args["min_age_days"] == 14
    assert call_args["limit"] == 25
