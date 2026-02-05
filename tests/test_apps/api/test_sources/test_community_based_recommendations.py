from unittest.mock import MagicMock

import pytest
from qdrant_client.http.exceptions import UnexpectedResponse

from apps.api.sources.statuses import CommunityBasedRecommendationsSource


@pytest.fixture
def mock_redis():
    return MagicMock()


@pytest.fixture
def mock_qdrant():
    return MagicMock()


def test_collect_returns_early_when_version_is_none(mock_redis, mock_qdrant):
    """Verify collect() handles None from Redis gracefully."""
    mock_redis.get.return_value = None

    source = CommunityBasedRecommendationsSource(
        r=mock_redis,
        client=mock_qdrant,
        account_id=123,
    )

    result = list(source.collect(limit=10))

    assert result == []
    mock_qdrant.query_points.assert_not_called()


def test_collect_decodes_version_and_queries(mock_redis, mock_qdrant):
    """Verify collect() uses version from Redis to query Qdrant."""
    mock_redis.get.return_value = b"v1"

    mock_point = MagicMock()
    mock_point.id = 456
    mock_qdrant.query_points.return_value = MagicMock(points=[mock_point])

    source = CommunityBasedRecommendationsSource(
        r=mock_redis,
        client=mock_qdrant,
        account_id=123,
    )

    result = list(source.collect(limit=10))

    assert result == [456]
    mock_qdrant.query_points.assert_called_once()
    call_kwargs = mock_qdrant.query_points.call_args.kwargs
    assert call_kwargs["collection_name"] == "orbit_v1_statuses"


def test_collect_handles_qdrant_error(mock_redis, mock_qdrant):
    """Verify collect() handles Qdrant errors gracefully."""
    mock_redis.get.return_value = b"v1"
    mock_qdrant.query_points.side_effect = UnexpectedResponse(
        status_code=500, reason_phrase="Internal Error", content=b"", headers={}
    )

    source = CommunityBasedRecommendationsSource(
        r=mock_redis,
        client=mock_qdrant,
        account_id=123,
    )

    result = list(source.collect(limit=10))

    assert result == []


def test_collect_yields_multiple_points(mock_redis, mock_qdrant):
    """Verify collect() yields all points from Qdrant response."""
    mock_redis.get.return_value = b"v2"

    mock_points = [MagicMock(id=i) for i in [100, 200, 300]]
    mock_qdrant.query_points.return_value = MagicMock(points=mock_points)

    source = CommunityBasedRecommendationsSource(
        r=mock_redis,
        client=mock_qdrant,
        account_id=123,
    )

    result = list(source.collect(limit=10))

    assert result == [100, 200, 300]


def test_source_has_correct_id():
    mock_redis = MagicMock()
    mock_qdrant = MagicMock()

    source = CommunityBasedRecommendationsSource(
        r=mock_redis,
        client=mock_qdrant,
        account_id=123,
    )

    assert source.id == "community_based_recommendations"
