from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from apps.api.sources.statuses import TopFollowsSource


def test_source_id():
    mock_rw = MagicMock()
    source = TopFollowsSource(rw=mock_rw, account_id=1)
    assert source.id == "top_follows"


def test_source_tracked_params():
    mock_rw = MagicMock()
    source = TopFollowsSource(
        rw=mock_rw,
        account_id=1,
        recency_half_life_hours=6,
        max_age_hours=24,
        max_per_author=2,
    )
    params = source.get_params()
    assert params == {
        "recency_half_life_hours": 6,
        "max_age_hours": 24,
        "max_per_author": 2,
    }


def test_collect_empty_affinities():
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = []

    source = TopFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result == []


def _mock_execute_factory(affinities, followed_ids, statuses):
    def mock_execute(query, params):
        query_str = str(query)
        mock_result = MagicMock()
        if "user_followed_affinity" in query_str:
            mock_result.fetchall.return_value = affinities
        elif "target_account_id" in query_str and "statuses" not in query_str:
            mock_result.fetchall.return_value = [(fid,) for fid in followed_ids]
        elif "statuses" in query_str:
            mock_result.fetchall.return_value = statuses
        else:
            mock_result.fetchall.return_value = []
        return mock_result

    return mock_execute


def test_collect_returns_status_ids():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _mock_execute_factory(
        affinities=[
            (201, 5.0, 0.0, 5.0, "direct"),
            (202, 3.0, 0.0, 3.0, "direct"),
        ],
        followed_ids=[201, 202],
        statuses=[
            (101, 201, now - timedelta(hours=1)),
            (102, 202, now - timedelta(hours=2)),
        ],
    )

    source = TopFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert 101 in result
    assert 102 in result


def test_scoring_favors_high_affinity():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _mock_execute_factory(
        affinities=[
            (201, 50.0, 0.0, 50.0, "direct"),
            (202, 1.0, 0.0, 1.0, "direct"),
        ],
        followed_ids=[201, 202],
        statuses=[
            (101, 201, now),
            (102, 202, now),
        ],
    )

    source = TopFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 101


def test_scoring_favors_recent_posts():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _mock_execute_factory(
        affinities=[(201, 5.0, 0.0, 5.0, "direct")],
        followed_ids=[201],
        statuses=[
            (101, 201, now - timedelta(hours=24)),
            (102, 201, now - timedelta(hours=1)),
        ],
    )

    source = TopFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 102


def test_diversity_limits_per_author():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _mock_execute_factory(
        affinities=[
            (201, 10.0, 0.0, 10.0, "direct"),
            (202, 5.0, 0.0, 5.0, "direct"),
        ],
        followed_ids=[201, 202],
        statuses=[
            (101, 201, now),
            (102, 201, now - timedelta(minutes=1)),
            (103, 201, now - timedelta(minutes=2)),
            (104, 201, now - timedelta(minutes=3)),
            (105, 202, now - timedelta(minutes=4)),
        ],
    )

    source = TopFollowsSource(rw=mock_rw, account_id=1, max_per_author=2)
    result = source.collect(10)

    author_201_count = sum(1 for sid in result if sid in [101, 102, 103, 104])
    assert author_201_count == 2
    assert 105 in result


def test_cold_start_equal_weights():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _mock_execute_factory(
        affinities=[],
        followed_ids=[201, 202],
        statuses=[
            (101, 201, now),
            (102, 202, now),
        ],
    )

    source = TopFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert len(result) == 2


def test_inferred_affinity_used():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _mock_execute_factory(
        affinities=[
            (201, 0.0, 10.0, 7.0, "inferred"),
            (202, 5.0, 0.0, 5.0, "direct"),
        ],
        followed_ids=[201, 202],
        statuses=[
            (101, 201, now),
            (102, 202, now),
        ],
    )

    source = TopFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(10)

    assert result[0] == 101


def test_respects_limit():
    mock_rw = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    mock_rw.execute.side_effect = _mock_execute_factory(
        affinities=[(200 + i, 10.0 - i, 0.0, 10.0 - i, "direct") for i in range(10)],
        followed_ids=[200 + i for i in range(10)],
        statuses=[(100 + i, 200 + i, now - timedelta(minutes=i)) for i in range(10)],
    )

    source = TopFollowsSource(rw=mock_rw, account_id=1)
    result = source.collect(5)

    assert len(result) == 5
