from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from apps.api.sources.statuses import EngagedBySimilarUsersSource, PopularPostsSource

# -- EngagedBySimilarUsersSource --


def test_engaged_by_similar_users_source_id():
    source = EngagedBySimilarUsersSource(rw=MagicMock(), account_id=1)
    assert source.id == "engaged_by_similar_users"


def test_engaged_by_similar_users_tracked_params():
    source = EngagedBySimilarUsersSource(
        rw=MagicMock(),
        account_id=1,
        min_similarity=0.1,
        max_per_author=3,
    )
    assert source.get_params() == {"min_similarity": 0.1, "max_per_author": 3}


def test_engaged_by_similar_users_collect_empty():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    assert EngagedBySimilarUsersSource(rw=mock_rw, account_id=1).collect(10) == []


def _make_similar_users_execute(engagements, followed_ids=None):
    followed_ids = followed_ids or []

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "similar_user_recent_engagements" in query_str:
            mock_result.fetchall.return_value = engagements
        elif "follows" in query_str:
            mock_result.fetchall.return_value = [(fid,) for fid in followed_ids]
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    return mock_execute


def test_engaged_by_similar_users_filters_followed_authors():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _make_similar_users_execute(
        engagements=[
            (101, 201, 0.2, 2.0, now),
            (102, 202, 0.2, 2.0, now),
        ],
        followed_ids=[201],
    )

    result = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1).collect(10)

    assert 101 not in result
    assert 102 in result


def test_engaged_by_similar_users_aggregates_multiple_engagements():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _make_similar_users_execute(
        engagements=[
            (101, 201, 0.2, 2.0, now),
            (101, 201, 0.3, 1.0, now),
            (102, 202, 0.1, 1.0, now),
        ],
    )

    result = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1).collect(10)

    assert result[0] == 101


def test_engaged_by_similar_users_diversity_limits_per_author():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _make_similar_users_execute(
        engagements=[
            (101, 201, 0.3, 3.0, now),
            (102, 201, 0.3, 2.5, now),
            (103, 201, 0.3, 2.0, now),
            (104, 202, 0.3, 1.5, now),
        ],
    )

    result = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1, max_per_author=2).collect(10)

    author_201_count = sum(1 for sid in result if sid in [101, 102, 103])
    assert author_201_count == 2
    assert 104 in result


def test_engaged_by_similar_users_scoring_uses_recency():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _make_similar_users_execute(
        engagements=[
            (101, 201, 0.5, 2.0, now - timedelta(hours=24)),
            (102, 202, 0.5, 2.0, now),
        ],
    )

    result = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1).collect(10)

    assert result[0] == 102


# -- PopularPostsSource --


def test_popular_posts_source_id():
    assert PopularPostsSource(rw=MagicMock(), account_id=1).id == "popular_posts"


def test_popular_posts_collect_empty():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    assert PopularPostsSource(rw=mock_rw, account_id=1).collect(10) == []


def _make_popular_posts_execute(posts, followed_ids=None):
    followed_ids = followed_ids or []

    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "follows" in query_str:
            mock_result.fetchall.return_value = [(fid,) for fid in followed_ids]
        elif "popular_posts" in query_str:
            mock_result.fetchall.return_value = posts
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    return mock_execute


def test_popular_posts_filters_followed():
    mock_rw = MagicMock()
    mock_rw.execute.side_effect = _make_popular_posts_execute(
        posts=[
            (101, 201, 10, 25.0),
            (102, 202, 8, 20.0),
        ],
        followed_ids=[201],
    )

    result = PopularPostsSource(rw=mock_rw, account_id=1).collect(10)

    assert 101 not in result
    assert 102 in result


def test_popular_posts_applies_diversity():
    mock_rw = MagicMock()
    mock_rw.execute.side_effect = _make_popular_posts_execute(
        posts=[
            (101, 201, 10, 30.0),
            (102, 201, 9, 25.0),
            (103, 201, 8, 20.0),
            (104, 202, 7, 15.0),
        ],
    )

    result = PopularPostsSource(rw=mock_rw, account_id=1, max_per_author=2).collect(10)

    author_201_count = sum(1 for sid in result if sid in [101, 102, 103])
    assert author_201_count == 2
    assert 104 in result
