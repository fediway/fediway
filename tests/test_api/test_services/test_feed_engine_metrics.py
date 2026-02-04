"""
Tests for FeedEngine metrics emission.

These tests verify that FeedEngine emits the correct data to Kafka topics.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.services.feed_engine import CODE_VERSION, FeedEngine


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.client.host = "192.168.1.100"
    request.headers.get.return_value = "FediwayTest/1.0"
    return request


@pytest.fixture
def mock_kafka():
    kafka = MagicMock()
    kafka.send.return_value = MagicMock()
    return kafka


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get.return_value = None
    return redis


@pytest.fixture
def mock_tasks():
    return MagicMock()


@pytest.fixture
def mock_account():
    account = MagicMock()
    account.id = 456
    return account


@pytest.fixture
def mock_pipeline():
    from modules.fediway.feed.steps import SourcingStep

    pipeline = MagicMock()
    pipeline.counter = 3
    pipeline.event_time = datetime(2024, 1, 15, 12, 0, 0)
    pipeline.get_durations.return_value = [1000000, 2000000, 500000]

    sourcing_step = MagicMock(spec=SourcingStep)
    sourcing_step.__class__ = SourcingStep
    sourcing_step.get_params.return_value = {"group": "in-network"}
    sourcing_step.get_durations.return_value = [100000, 200000]
    sourcing_step.get_counts.return_value = [50, 30]
    sourcing_step.get_sourced_candidates.return_value = [{1, 2, 3}, {4, 5}]
    sourcing_step.group = "in-network"

    mock_source = MagicMock()
    mock_source.id = "smart_follows"
    mock_source.get_params.return_value = {"max_per_author": 3}
    sourcing_step.sources = [(mock_source, 100), (MagicMock(id="tag_affinity"), 50)]

    pipeline.steps = [sourcing_step, MagicMock()]
    pipeline.steps[1].__class__.__name__ = "SamplingStep"
    pipeline.steps[1].get_params.return_value = {"n": 20}

    return pipeline


@pytest.fixture
def mock_feed(mock_pipeline):
    from modules.fediway.feed.candidates import CandidateList

    feed = MagicMock()
    feed.entity = "status_id"
    feed.__class__.__name__ = "HomeFeed"
    feed.pipeline = mock_pipeline

    candidates = CandidateList("status_id")
    candidates.append(101, score=0.95, source="smart_follows", source_group="in-network")
    candidates.append(102, score=0.87, source="tag_affinity", source_group="discovery")
    candidates.append(103, score=0.72, source="viral", source_group="trending")
    feed.execute = AsyncMock(return_value=candidates)
    feed.flush = MagicMock()

    return feed


def test_emit_metrics_sends_feed_record(
    mock_kafka, mock_redis, mock_request, mock_tasks, mock_account, mock_feed
):
    from modules.fediway.feed.candidates import CandidateList

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    results = CandidateList("status_id")
    results.append(101, score=0.95, source="s1", source_group="g1")

    engine._emit_metrics(mock_feed, results)

    feed_calls = [c for c in mock_kafka.send.call_args_list if c[1]["topic"] == "feeds"]
    assert len(feed_calls) == 1

    feed_data = feed_calls[0][1]["value"]
    assert feed_data["name"] == "HomeFeed"
    assert feed_data["entity"] == "status_id"
    assert feed_data["account_id"] == 456
    assert feed_data["user_agent"] == "FediwayTest/1.0"
    assert feed_data["ip"] == "192.168.1.100"
    assert "event_time" in feed_data


def test_emit_metrics_sends_pipeline_run(
    mock_kafka, mock_redis, mock_request, mock_tasks, mock_account, mock_feed
):
    from modules.fediway.feed.candidates import CandidateList

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    results = CandidateList("status_id")

    engine._emit_metrics(mock_feed, results)

    run_calls = [c for c in mock_kafka.send.call_args_list if c[1]["topic"] == "feed_pipeline_runs"]
    assert len(run_calls) == 1

    run_data = run_calls[0][1]["value"]
    assert run_data["iteration"] == 3
    assert run_data["duration_ns"] == 3500000
    assert run_data["code_version"] == CODE_VERSION


def test_emit_metrics_sends_pipeline_steps(
    mock_kafka, mock_redis, mock_request, mock_tasks, mock_account, mock_feed
):
    from modules.fediway.feed.candidates import CandidateList

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    results = CandidateList("status_id")

    engine._emit_metrics(mock_feed, results)

    step_calls = [
        c for c in mock_kafka.send.call_args_list if c[1]["topic"] == "feed_pipeline_steps"
    ]
    assert len(step_calls) == 2

    step_names = [c[1]["value"]["name"] for c in step_calls]
    assert "SourcingStep" in step_names
    assert "SamplingStep" in step_names


def test_emit_metrics_sends_sourcing_runs(
    mock_kafka, mock_redis, mock_request, mock_tasks, mock_account, mock_feed
):
    from modules.fediway.feed.candidates import CandidateList

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    results = CandidateList("status_id")

    engine._emit_metrics(mock_feed, results)

    sourcing_calls = [
        c for c in mock_kafka.send.call_args_list if c[1]["topic"] == "feed_sourcing_runs"
    ]
    assert len(sourcing_calls) == 2

    sources = [c[1]["value"]["source"] for c in sourcing_calls]
    assert "smart_follows" in sources
    assert "tag_affinity" in sources

    smart_follows_call = next(
        c for c in sourcing_calls if c[1]["value"]["source"] == "smart_follows"
    )
    assert smart_follows_call[1]["value"]["candidates_limit"] == 100
    assert smart_follows_call[1]["value"]["candidates_count"] == 50


def test_emit_metrics_sends_candidate_sources(
    mock_kafka, mock_redis, mock_request, mock_tasks, mock_account, mock_feed
):
    from modules.fediway.feed.candidates import CandidateList

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    results = CandidateList("status_id")

    engine._emit_metrics(mock_feed, results)

    candidate_calls = [
        c for c in mock_kafka.send.call_args_list if c[1]["topic"] == "feed_candidate_sources"
    ]
    assert len(candidate_calls) == 5


def test_emit_metrics_sends_recommendations(
    mock_kafka, mock_redis, mock_request, mock_tasks, mock_account, mock_feed
):
    from modules.fediway.feed.candidates import CandidateList

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    results = CandidateList("status_id")
    results.append(101, score=0.95, source="smart_follows", source_group="in-network")
    results.append(102, score=0.87, source="tag_affinity", source_group="discovery")

    engine._emit_metrics(mock_feed, results)

    rec_calls = [
        c for c in mock_kafka.send.call_args_list if c[1]["topic"] == "feed_recommendations"
    ]
    assert len(rec_calls) == 2

    rec_data = rec_calls[0][1]["value"]
    assert rec_data["entity"] == "status_id"
    assert rec_data["entity_id"] == 101
    assert rec_data["score"] == 0.95
    assert "smart_follows" in rec_data["sources"]
    assert "in-network" in rec_data["groups"]


def test_emit_metrics_handles_no_pipeline(
    mock_kafka, mock_redis, mock_request, mock_tasks, mock_account
):
    from modules.fediway.feed.candidates import CandidateList

    feed = MagicMock()
    feed.pipeline = None

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    results = CandidateList("status_id")

    engine._emit_metrics(feed, results)

    mock_kafka.send.assert_not_called()


def test_emit_metrics_handles_kafka_error(
    mock_kafka, mock_redis, mock_request, mock_tasks, mock_account, mock_feed
):
    from modules.fediway.feed.candidates import CandidateList

    mock_kafka.send.side_effect = Exception("Kafka unavailable")

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    results = CandidateList("status_id")

    engine._emit_metrics(mock_feed, results)


def test_emit_metrics_handles_none_client(
    mock_kafka, mock_redis, mock_tasks, mock_account, mock_feed
):
    from modules.fediway.feed.candidates import CandidateList

    request = MagicMock()
    request.client = None
    request.headers.get.return_value = "Test/1.0"

    engine = FeedEngine(mock_kafka, mock_redis, request, mock_tasks, mock_account)
    results = CandidateList("status_id")

    engine._emit_metrics(mock_feed, results)

    feed_calls = [c for c in mock_kafka.send.call_args_list if c[1]["topic"] == "feeds"]
    assert feed_calls[0][1]["value"]["ip"] is None


def test_emit_metrics_flushes_kafka(
    mock_kafka, mock_redis, mock_request, mock_tasks, mock_account, mock_feed
):
    from modules.fediway.feed.candidates import CandidateList

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    results = CandidateList("status_id")

    engine._emit_metrics(mock_feed, results)

    mock_kafka.flush.assert_called_once()
