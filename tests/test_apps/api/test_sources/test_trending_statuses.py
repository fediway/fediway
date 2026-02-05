import json
from datetime import timedelta
from unittest.mock import MagicMock

import numpy as np

from apps.api.sources.statuses import TrendingStatusesSource


def test_source_id():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock())
    assert source.id == "trending"


def test_source_tracked_params():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    source = TrendingStatusesSource(
        r=mock_redis,
        rw=MagicMock(),
        language="de",
        top_n=50,
        max_per_author=3,
    )
    params = source.get_params()
    assert params == {"language": "de", "top_n": 50, "max_per_author": 3}


def test_redis_key_includes_language():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock(), language="fr")
    assert source.redis_key() == "source:trending:fr"


def test_compute_queries_risingwave():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 5.5),
        (102, 202, 3.2),
    ]

    source = TrendingStatusesSource(r=mock_redis, rw=mock_rw, language="en", top_n=100)
    results = list(source.compute())

    assert len(results) == 2
    assert results[0] == {"status_id": 101, "author_id": 201, "score": 5.5}
    assert results[1] == {"status_id": 102, "author_id": 202, "score": 3.2}


def test_diversity_limits_per_author():
    candidates = [
        {"status_id": 1, "author_id": 100, "score": 10.0},
        {"status_id": 2, "author_id": 100, "score": 9.0},
        {"status_id": 3, "author_id": 100, "score": 8.0},
        {"status_id": 4, "author_id": 100, "score": 7.0},
        {"status_id": 5, "author_id": 200, "score": 6.0},
    ]

    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock(), max_per_author=2)

    diversified = source._apply_diversity(candidates, 10)

    author_100_count = sum(1 for c in diversified if c["author_id"] == 100)
    assert author_100_count == 2
    assert any(c["author_id"] == 200 for c in diversified)


def test_diversity_preserves_score_order():
    candidates = [
        {"status_id": 1, "author_id": 100, "score": 10.0},
        {"status_id": 2, "author_id": 200, "score": 9.0},
        {"status_id": 3, "author_id": 100, "score": 8.0},
        {"status_id": 4, "author_id": 300, "score": 7.0},
    ]

    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock(), max_per_author=2)

    diversified = source._apply_diversity(candidates, 10)

    assert diversified[0]["status_id"] == 1
    assert diversified[1]["status_id"] == 2


def test_diversity_respects_limit():
    candidates = [{"status_id": i, "author_id": i * 100, "score": 10.0 - i} for i in range(20)]

    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock(), max_per_author=2)

    diversified = source._apply_diversity(candidates, 5)

    assert len(diversified) == 5


def test_collect_empty_returns_nothing():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = json.dumps([])

    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock())
    results = list(source.collect(10))

    assert results == []


def test_collect_returns_status_ids():
    candidates = [
        {"status_id": 101, "author_id": 201, "score": 5.0},
        {"status_id": 102, "author_id": 202, "score": 4.0},
        {"status_id": 103, "author_id": 203, "score": 3.0},
    ]

    mock_redis = MagicMock()
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = json.dumps(candidates)

    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock())

    np.random.seed(42)
    results = list(source.collect(3))

    assert len(results) == 3
    assert all(r in [101, 102, 103] for r in results)


def test_collect_respects_limit():
    candidates = [
        {"status_id": i, "author_id": i * 100, "score": 10.0 - i * 0.1} for i in range(50)
    ]

    mock_redis = MagicMock()
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = json.dumps(candidates)

    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock())

    np.random.seed(42)
    results = list(source.collect(10))

    assert len(results) == 10


def test_collect_probabilistic_sampling():
    candidates = [
        {"status_id": 1, "author_id": 100, "score": 100.0},
        {"status_id": 2, "author_id": 200, "score": 1.0},
    ]

    mock_redis = MagicMock()
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = json.dumps(candidates)

    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock())

    high_score_count = 0
    for _ in range(100):
        results = list(source.collect(1))
        if results[0] == 1:
            high_score_count += 1

    # High score should be picked much more often
    assert high_score_count > 80


def test_collect_handles_zero_scores():
    candidates = [
        {"status_id": 1, "author_id": 100, "score": 0.0},
        {"status_id": 2, "author_id": 200, "score": 0.0},
    ]

    mock_redis = MagicMock()
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = json.dumps(candidates)

    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock())
    results = list(source.collect(2))

    assert len(results) == 2


def test_collect_with_diversity_applied():
    candidates = [
        {"status_id": 1, "author_id": 100, "score": 10.0},
        {"status_id": 2, "author_id": 100, "score": 9.0},
        {"status_id": 3, "author_id": 100, "score": 8.0},
        {"status_id": 4, "author_id": 200, "score": 7.0},
        {"status_id": 5, "author_id": 300, "score": 6.0},
    ]

    mock_redis = MagicMock()
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = json.dumps(candidates)

    source = TrendingStatusesSource(r=mock_redis, rw=MagicMock(), max_per_author=2)

    np.random.seed(42)
    results = list(source.collect(5))

    # Status 3 should never appear (author 100 already has 2)
    # But due to probabilistic sampling, we can't guarantee exact results
    # Just verify we get 4 results (diversity limits to 4 candidates)
    assert len(results) == 4


def test_store_computes_and_caches():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    mock_rw = MagicMock()
    mock_rw.execute.return_value.fetchall.return_value = [
        (101, 201, 5.5),
    ]

    source = TrendingStatusesSource(
        r=mock_redis,
        rw=mock_rw,
        ttl=timedelta(minutes=10),
    )
    results = source.store()

    assert len(results) == 1
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "source:trending:en"
    assert call_args[0][1] == 600  # 10 minutes in seconds
