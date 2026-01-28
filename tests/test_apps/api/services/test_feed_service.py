import json
import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import BackgroundTasks, Request

from apps.api.services.feed_service import (
    FeedService,
    _generate_feed_id,
    _get_feed_key,
    request_key,
)


def test_request_key_combines_host_and_user_agent():
    mock_request = Mock(spec=Request)
    mock_request.client.host = "192.168.1.1"
    mock_request.headers.get.return_value = "Mozilla/5.0"

    result = request_key(mock_request)

    assert result == "192.168.1.1.Mozilla/5.0"


@patch("apps.api.services.feed_service.uuid.uuid4")
def test_generate_feed_id_returns_shortened_uuid(mock_uuid):
    mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
    mock_request = Mock(spec=Request)

    result = _generate_feed_id(mock_request, length=8)

    assert result == "12345678"
    assert len(result) == 8


def test_get_feed_key_returns_hashed_key():
    mock_request = Mock(spec=Request)
    mock_request.client.host = "192.168.1.1"
    mock_request.headers.get.return_value = "Mozilla/5.0"

    result = _get_feed_key(mock_request, length=32)

    assert len(result) == 32
    assert isinstance(result, str)


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_init_sets_all_attributes(mock_feed, mock_gen_id, mock_get_key):
    mock_kafka = Mock()
    mock_request = Mock(spec=Request)
    mock_tasks = Mock(spec=BackgroundTasks)
    mock_redis = Mock()
    mock_feature_service = Mock()
    mock_account = Mock()

    mock_gen_id.return_value = "abc123"
    mock_get_key.return_value = "key456"

    service = FeedService(
        kafka=mock_kafka,
        request=mock_request,
        tasks=mock_tasks,
        redis=mock_redis,
        feature_service=mock_feature_service,
        account=mock_account,
    )

    assert service.kafka == mock_kafka
    assert service.request == mock_request
    assert service.tasks == mock_tasks
    assert service.r == mock_redis
    assert service.feature_service == mock_feature_service
    assert service.account == mock_account
    assert service.id == "abc123"
    assert service.key == "key456"
    assert service._name is None
    mock_feed.assert_called_once_with(mock_feature_service)


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_redis_key_property(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    service._name = "test_feed"
    service.key = "testkey123"

    assert service.redis_key == "feed:test_feed:testkey123"


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_event_time_property(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    mock_timestamp = Mock()
    mock_timestamp.timestamp.return_value = 1234567890.5
    service.feature_service.event_time = mock_timestamp

    assert service.event_time == 1234567890


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_name_sets_name_and_returns_self(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    result = service.name("home_feed")

    assert service._name == "home_feed"
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_source_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    mock_source = Mock()

    result = service.source(mock_source, 10, "group1")

    service.pipeline.source.assert_called_once_with(mock_source, 10, "group1")
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_remember_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    result = service.remember()

    service.pipeline.remember.assert_called_once()
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_sources_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    sources = [(Mock(), 5), (Mock(), 10)]

    result = service.sources(sources, "group1")

    service.pipeline.sources.assert_called_once_with(sources, "group1")
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_select_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    result = service.select("status")

    service.pipeline.select.assert_called_once_with("status")
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_unique_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    result = service.unique()

    service.pipeline.unique.assert_called_once()
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_rank_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    mock_ranker = Mock()
    mock_features = Mock()

    result = service.rank(mock_ranker, mock_features)

    service.pipeline.rank.assert_called_once_with(mock_ranker, mock_features)
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_sample_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    mock_sampler = Mock()

    result = service.sample(20, mock_sampler)

    service.pipeline.sample.assert_called_once_with(20, mock_sampler)
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_paginate_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    result = service.paginate(50, 10, 12345)

    service.pipeline.paginate.assert_called_once_with(50, 10, 12345)
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_heuristic_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    mock_heuristic = Mock()

    result = service.heuristic(mock_heuristic)

    service.pipeline.heuristic.assert_called_once_with(mock_heuristic)
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_diversify_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    result = service.diversify("author", 0.2)

    service.pipeline.diversify.assert_called_once_with("author", 0.2)
    assert result is service


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_passthrough_delegates_to_pipeline(mock_feed, mock_gen_id, mock_get_key):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    mock_callback = Mock()

    result = service.passthrough(mock_callback)

    service.pipeline.passthrough.assert_called_once_with(mock_callback)
    assert result is service


@patch("apps.api.services.feed_service.config")
@patch("apps.api.services.feed_service.Feed")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service._get_feed_key")
def test_save_state_stores_in_redis(mock_get_key, mock_gen_id, mock_feed, mock_config):
    mock_config.fediway.feed_session_ttl = 3600
    mock_redis = Mock()
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=mock_redis,
        feature_service=Mock(),
        account=None,
    )
    service._name = "test_feed"
    service.id = "feed123"
    service.pipeline.get_state.return_value = {"counter": 1}

    service._save_state()

    service.r.setex.assert_called_once()
    call_args = service.r.setex.call_args
    assert call_args[0][0] == service.redis_key
    assert call_args[0][1] == 3600

    state_data = json.loads(call_args[0][2])
    assert state_data["id"] == "feed123"
    assert state_data["pipeline"] == {"counter": 1}


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_load_state_when_state_exists(mock_feed, mock_gen_id, mock_get_key):
    mock_redis = Mock()
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=mock_redis,
        feature_service=Mock(),
        account=None,
    )
    service._name = "test_feed"
    service.r.exists.return_value = True

    state = {"id": "saved_feed_id", "pipeline": {"counter": 5}}
    service.r.get.return_value = json.dumps(state)

    service._load_state()

    service.r.exists.assert_called_once_with(service.redis_key)
    service.r.get.assert_called_once_with(service.redis_key)
    service.pipeline.set_state.assert_called_once_with({"counter": 5})
    assert service.id == "saved_feed_id"


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_load_state_when_no_state_exists(mock_feed, mock_gen_id, mock_get_key):
    mock_redis = Mock()
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=mock_redis,
        feature_service=Mock(),
        account=None,
    )
    service._name = "test_feed"
    service.r.exists.return_value = False

    service._load_state()

    service.r.exists.assert_called_once_with(service.redis_key)
    service.r.get.assert_not_called()
    service.pipeline.set_state.assert_not_called()


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_flush_deletes_redis_key(mock_feed, mock_gen_id, mock_get_key):
    mock_redis = Mock()
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=mock_redis,
        feature_service=Mock(),
        account=None,
    )
    service._name = "test_feed"

    service.flush()

    service.r.delete.assert_called_once_with(service.redis_key)


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_send_kafka_message(mock_feed, mock_gen_id, mock_get_key):
    mock_kafka = Mock()
    service = FeedService(
        kafka=mock_kafka,
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    service._send_kafka_message("test_topic", "key123", {"data": "value"})

    service.kafka.send.assert_called_once_with(
        topic="test_topic", key="key123", value={"data": "value"}
    )


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_ingest_feed(mock_feed, mock_gen_id, mock_get_key):
    mock_kafka = Mock()
    mock_request = Mock(spec=Request)
    mock_request.headers.get.return_value = "Mozilla/5.0"
    mock_request.client.host = "192.168.1.1"

    service = FeedService(
        kafka=mock_kafka,
        request=mock_request,
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=Mock(id="account456"),
    )
    service.id = "feed123"
    service._name = "home_feed"
    service.pipeline.entity = "status"

    mock_timestamp = Mock()
    mock_timestamp.timestamp.return_value = 1234567890.0
    service.feature_service.event_time = mock_timestamp

    service._ingest_feed()

    service.kafka.send.assert_called_once()
    call_args = service.kafka.send.call_args
    assert call_args[1]["topic"] == "feeds"
    assert call_args[1]["key"] == "feed123"
    assert call_args[1]["value"]["id"] == "feed123"
    assert call_args[1]["value"]["name"] == "home_feed"
    assert call_args[1]["value"]["entity"] == "status"
    assert call_args[1]["value"]["account_id"] == "account456"


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_ingest_pipeline_run(mock_feed, mock_gen_id, mock_get_key):
    mock_kafka = Mock()
    service = FeedService(
        kafka=mock_kafka,
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    service.id = "feed123"
    service.pipeline.counter = 3
    service.pipeline.get_durations.return_value = [100, 200, 300]

    mock_timestamp = Mock()
    mock_timestamp.timestamp.return_value = 1234567890.0
    service.feature_service.event_time = mock_timestamp

    service._ingest_pipeline_run("run123")

    service.kafka.send.assert_called_once()
    call_args = service.kafka.send.call_args
    assert call_args[1]["topic"] == "feed_pipeline_runs"
    assert call_args[1]["key"] == "run123"
    assert call_args[1]["value"]["id"] == "run123"
    assert call_args[1]["value"]["feed_id"] == "feed123"
    assert call_args[1]["value"]["iteration"] == 2
    assert call_args[1]["value"]["duration_ns"] == 600


@patch("apps.api.services.feed_service.np")
@patch("apps.api.services.feed_service.uuid")
@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_ingest_recommendations(mock_feed, mock_gen_id, mock_get_key, mock_uuid, mock_np):
    mock_uuid.uuid4.side_effect = [
        uuid.UUID("11111111-1111-1111-1111-111111111111"),
        uuid.UUID("22222222-2222-2222-2222-222222222222"),
    ]
    mock_np.clip.side_effect = lambda x, *args, **kwargs: x

    mock_kafka = Mock()
    service = FeedService(
        kafka=mock_kafka,
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    service.id = "feed123"
    service.pipeline.entity = "status"

    mock_rec1 = Mock()
    mock_rec1.id = "rec1"
    mock_rec1.sources = [("source1", "group1"), ("source2", "group2")]
    mock_rec1.score = 0.95

    mock_rec2 = Mock()
    mock_rec2.id = "rec2"
    mock_rec2.sources = [("source3", "group1")]
    mock_rec2.score = 0.85

    service.pipeline.results.return_value = [mock_rec1, mock_rec2]

    mock_timestamp = Mock()
    mock_timestamp.timestamp.return_value = 1234567890.0
    service.feature_service.event_time = mock_timestamp

    futures = service._ingest_recommendations("run123")

    assert len(futures) == 2
    assert service.kafka.send.call_count == 2

    first_call = service.kafka.send.call_args_list[0]
    assert first_call[1]["topic"] == "feed_recommendations"
    assert first_call[1]["value"]["entity_id"] == "rec1"
    assert first_call[1]["value"]["sources"] == ["source1", "source2"]
    assert first_call[1]["value"]["groups"] == ["group1", "group2"]


@patch("apps.api.services.feed_service.uuid")
@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_ingest_pipeline_steps(mock_feed, mock_gen_id, mock_get_key, mock_uuid):
    mock_uuid.uuid4.side_effect = [
        uuid.UUID("11111111-1111-1111-1111-111111111111"),
        uuid.UUID("22222222-2222-2222-2222-222222222222"),
    ]

    mock_kafka = Mock()
    service = FeedService(
        kafka=mock_kafka,
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    service.id = "feed123"

    step1 = Mock()
    step1.__str__ = Mock(return_value="Step1")
    step1.get_params.return_value = {"param1": "value1"}

    step2 = Mock()
    step2.__str__ = Mock(return_value="Step2")
    step2.get_params.return_value = {}

    service.pipeline.steps = [step1, step2]
    service.pipeline.get_durations.return_value = [100, 200]

    mock_timestamp = Mock()
    mock_timestamp.timestamp.return_value = 1234567890.0
    service.feature_service.event_time = mock_timestamp

    step_ids, futures = service._ingest_pipeline_steps("run123")

    assert len(step_ids) == 2
    assert len(futures) == 2
    assert service.kafka.send.call_count == 2


@patch("apps.api.services.feed_service.uuid")
@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
@patch("apps.api.services.feed_service.SourcingStep")
def test_ingest_sourcing_runs(mock_sourcing_step, mock_feed, mock_gen_id, mock_get_key, mock_uuid):
    mock_uuid.uuid4.return_value = uuid.UUID("11111111-1111-1111-1111-111111111111")

    mock_kafka = Mock()
    service = FeedService(
        kafka=mock_kafka,
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    service.id = "feed123"
    service.pipeline.entity = "status"

    mock_source = Mock()
    mock_source.name.return_value = "TestSource"
    mock_source.get_params.return_value = {"param1": "value1"}

    step = Mock()
    step.sources = [(mock_source, 10)]
    step.get_durations.return_value = [150]
    step.get_counts.return_value = [8]
    step.get_sourced_candidates.return_value = [["cand1", "cand2"]]

    mock_timestamp = Mock()
    mock_timestamp.timestamp.return_value = 1234567890.0
    service.feature_service.event_time = mock_timestamp

    futures = service._ingest_sourcing_runs("step123", step)

    assert len(futures) > 0
    assert service.kafka.send.call_count >= 1


@patch("apps.api.services.feed_service.uuid")
@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
@patch("apps.api.services.feed_service.RankingStep")
def test_ingest_ranking_runs_with_duration(
    mock_ranking_step, mock_feed, mock_gen_id, mock_get_key, mock_uuid
):
    mock_uuid.uuid4.return_value = uuid.UUID("11111111-1111-1111-1111-111111111111")

    mock_kafka = Mock()
    service = FeedService(
        kafka=mock_kafka,
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    service.id = "feed123"

    step = Mock()
    step.get_ranking_duration.return_value = 250
    step.get_feature_retrieval_duration.return_value = 100
    step.get_candidates.return_value = ["cand1", "cand2", "cand3"]
    step.ranker.name = "TestRanker"

    mock_timestamp = Mock()
    mock_timestamp.timestamp.return_value = 1234567890.0
    service.feature_service.event_time = mock_timestamp

    futures = service._ingest_ranking_runs("step123", "run123", step)

    assert len(futures) == 1
    service.kafka.send.assert_called_once()


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
@patch("apps.api.services.feed_service.RankingStep")
def test_ingest_ranking_runs_without_duration(
    mock_ranking_step, mock_feed, mock_gen_id, mock_get_key
):
    mock_kafka = Mock()
    service = FeedService(
        kafka=mock_kafka,
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    step = Mock()
    step.get_ranking_duration.return_value = 0

    futures = service._ingest_ranking_runs("step123", "run123", step)

    assert len(futures) == 0
    service.kafka.send.assert_not_called()


@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_await_kafka_futures_success(mock_feed, mock_gen_id, mock_get_key):
    mock_kafka = Mock()
    service = FeedService(
        kafka=mock_kafka,
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    mock_future1 = Mock()
    mock_future2 = Mock()
    futures = [mock_future1, mock_future2]

    service._await_kafka_futures(futures)

    mock_future1.get.assert_called_once_with(timeout=10)
    mock_future2.get.assert_called_once_with(timeout=10)
    service.kafka.flush.assert_called_once()


@patch("apps.api.services.feed_service.logger")
@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
def test_await_kafka_futures_with_errors(mock_feed, mock_gen_id, mock_get_key, mock_logger):
    mock_kafka = Mock()
    service = FeedService(
        kafka=mock_kafka,
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )

    mock_future1 = Mock()
    mock_future1.get.side_effect = Exception("Kafka error")
    mock_future2 = Mock()

    futures = [mock_future1, mock_future2]

    service._await_kafka_futures(futures)

    mock_logger.error.assert_called_once()
    mock_future2.get.assert_called_once_with(timeout=10)
    service.kafka.flush.assert_called_once()


@patch("apps.api.services.feed_service.duration")
@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
@pytest.mark.asyncio
async def test_execute_pipeline(mock_feed, mock_gen_id, mock_get_key, mock_duration):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    service._save_state = Mock()
    service.pipeline.execute = AsyncMock()

    await service._execute()

    service.pipeline.execute.assert_called_once()
    service._save_state.assert_called_once()
    service.tasks.add_task.assert_called_once_with(service._save_pipeline_run)


@patch("apps.api.services.feed_service.duration")
@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
@pytest.mark.asyncio
async def test_execute_with_new_pipeline(mock_feed, mock_gen_id, mock_get_key, mock_duration):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    service._load_state = Mock()
    service._execute = AsyncMock()
    service.pipeline.is_new.return_value = True
    service.pipeline.results.return_value = ["rec1", "rec2", "rec3"]

    result = await service.execute()

    service._load_state.assert_called_once()
    service._execute.assert_called()
    assert service.tasks.add_task.call_count == 1
    assert result == ["rec1", "rec2", "rec3"]


@patch("apps.api.services.feed_service.duration")
@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
@pytest.mark.asyncio
async def test_execute_with_existing_pipeline(mock_feed, mock_gen_id, mock_get_key, mock_duration):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=None,
    )
    service._load_state = Mock()
    service._execute_pipeline = Mock()
    service.pipeline.is_new.return_value = False
    service.pipeline.results.return_value = ["rec1", "rec2"]

    result = await service.execute()

    service._load_state.assert_called_once()
    assert service.tasks.add_task.call_count == 1
    assert result == ["rec1", "rec2"]


@patch("apps.api.services.feed_service.duration")
@patch("apps.api.services.feed_service._get_feed_key")
@patch("apps.api.services.feed_service._generate_feed_id")
@patch("apps.api.services.feed_service.Feed")
@pytest.mark.asyncio
async def test_fluent_interface_chaining(mock_feed, mock_gen_id, mock_get_key, mock_duration):
    service = FeedService(
        kafka=Mock(),
        request=Mock(spec=Request),
        tasks=Mock(spec=BackgroundTasks),
        redis=Mock(),
        feature_service=Mock(),
        account=Mock(id="123"),
    )

    result = (
        service.name("test_feed")
        .select("status")
        .source(Mock(), 10)
        .unique()
        .rank(Mock())
        .sample(20)
        .paginate(50)
    )

    assert result is service
    assert service._name == "test_feed"
