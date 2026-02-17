from unittest.mock import MagicMock

from apps.api.sources.accounts import SimilarInterestsSource


def test_similar_interests_source_has_required_attributes():
    mock_rw = MagicMock()
    source = SimilarInterestsSource(rw=mock_rw, account_id=1)

    assert source.id == "similar_interests"
    assert "min_tag_overlap" in source._tracked_params
    assert "exclude_following" in source._tracked_params


def test_similar_interests_source_get_params():
    mock_rw = MagicMock()
    source = SimilarInterestsSource(
        rw=mock_rw,
        account_id=1,
        min_tag_overlap=5,
    )

    params = source.get_params()

    assert params["min_tag_overlap"] == 5
    assert params["exclude_following"] is True


def test_similar_interests_source_collect_returns_ids():
    mock_rw = MagicMock()

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "author_primary_tags" in query_str:
            mock_result.fetchall.return_value = [
                (100, 10),
                (200, 7),
            ]
        elif "follows" in query_str:
            mock_result.fetchall.return_value = []
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SimilarInterestsSource(rw=mock_rw, account_id=1)
    results = source.collect(limit=10)

    assert results == [100, 200]


def test_similar_interests_source_excludes_followed():
    mock_rw = MagicMock()

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "author_primary_tags" in query_str:
            mock_result.fetchall.return_value = [
                (100, 10),
                (200, 7),
            ]
        elif "follows" in query_str:
            mock_result.fetchall.return_value = [(100,)]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    mock_rw.execute.side_effect = mock_execute

    source = SimilarInterestsSource(rw=mock_rw, account_id=1)
    results = source.collect(limit=10)

    assert 100 not in results
    assert 200 in results


def test_similar_interests_source_includes_followed_when_disabled():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = [
        (100, 10),
        (200, 7),
    ]

    source = SimilarInterestsSource(rw=mock_rw, account_id=1, exclude_following=False)
    results = source.collect(limit=10)

    assert results == [100, 200]


def test_similar_interests_source_collect_returns_empty_on_no_results():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = SimilarInterestsSource(rw=mock_rw, account_id=1, exclude_following=False)
    results = source.collect(limit=10)

    assert results == []
