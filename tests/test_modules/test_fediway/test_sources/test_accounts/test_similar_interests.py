from unittest.mock import MagicMock

from modules.fediway.sources.accounts import SimilarInterestsSource


def test_similar_interests_source_has_required_attributes():
    mock_rw = MagicMock()
    source = SimilarInterestsSource(rw=mock_rw, account_id=1)

    assert source.id == "similar_interests"
    assert "min_tag_overlap" in source._tracked_params


def test_similar_interests_source_get_params():
    mock_rw = MagicMock()
    source = SimilarInterestsSource(
        rw=mock_rw,
        account_id=1,
        min_tag_overlap=5,
        lookback_days=60,
    )

    params = source.get_params()

    assert params["min_tag_overlap"] == 5
    assert params["lookback_days"] == 60


def test_similar_interests_source_collect_executes_query():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = [
        (100, 10),
        (200, 7),
    ]

    source = SimilarInterestsSource(rw=mock_rw, account_id=1)
    results = source.collect(limit=10)

    assert results == [100, 200]
    mock_rw.execute.assert_called_once()


def test_similar_interests_source_collect_returns_empty_on_no_results():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = SimilarInterestsSource(rw=mock_rw, account_id=1)
    results = source.collect(limit=10)

    assert results == []
