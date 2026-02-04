from unittest.mock import MagicMock

import pytest

from apps.api.dependencies.feeds import (
    get_feed_engine,
    get_home_feed,
    get_suggestions_feed,
    get_trending_statuses_feed,
    get_trending_tags_feed,
)


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers.get.return_value = "TestAgent/1.0"
    return request


@pytest.fixture
def mock_tasks():
    return MagicMock()


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get.return_value = None
    return redis


@pytest.fixture
def mock_kafka():
    return MagicMock()


@pytest.fixture
def mock_rw_session():
    return MagicMock()


@pytest.fixture
def mock_account():
    account = MagicMock()
    account.id = 123
    return account


@pytest.fixture
def mock_feature_service():
    return MagicMock()


def test_get_feed_engine_returns_engine(
    mock_request, mock_tasks, mock_redis, mock_kafka, mock_account
):
    from apps.api.services.feed_engine import FeedEngine

    engine = get_feed_engine(
        request=mock_request,
        tasks=mock_tasks,
        redis=mock_redis,
        kafka=mock_kafka,
        account=mock_account,
    )

    assert isinstance(engine, FeedEngine)


def test_get_feed_engine_without_account(mock_request, mock_tasks, mock_redis, mock_kafka):
    from apps.api.services.feed_engine import FeedEngine

    engine = get_feed_engine(
        request=mock_request,
        tasks=mock_tasks,
        redis=mock_redis,
        kafka=mock_kafka,
        account=None,
    )

    assert isinstance(engine, FeedEngine)
    assert engine._account is None


def test_get_home_feed_returns_home_feed(
    mock_rw_session, mock_redis, mock_account, mock_feature_service
):
    from apps.api.feeds import HomeFeed

    feed = get_home_feed(
        rw=mock_rw_session,
        redis=mock_redis,
        languages=["en", "de"],
        account=mock_account,
        feature_service=mock_feature_service,
    )

    assert isinstance(feed, HomeFeed)
    assert feed.account_id == 123
    assert feed.languages == ["en", "de"]


def test_get_home_feed_with_default_languages(
    mock_rw_session, mock_redis, mock_account, mock_feature_service
):
    from apps.api.feeds import HomeFeed

    feed = get_home_feed(
        rw=mock_rw_session,
        redis=mock_redis,
        languages=["en"],
        account=mock_account,
        feature_service=mock_feature_service,
    )

    assert isinstance(feed, HomeFeed)
    assert feed.languages == ["en"]


def test_get_suggestions_feed_returns_suggestions_feed(mock_rw_session, mock_account):
    from apps.api.feeds import SuggestionsFeed

    feed = get_suggestions_feed(rw=mock_rw_session, account=mock_account)

    assert isinstance(feed, SuggestionsFeed)
    assert feed.account_id == 123


def test_get_trending_statuses_feed_returns_trending_feed(mock_rw_session, mock_redis):
    from apps.api.feeds import TrendingStatusesFeed

    feed = get_trending_statuses_feed(rw=mock_rw_session, redis=mock_redis, languages=["en", "fr"])

    assert isinstance(feed, TrendingStatusesFeed)
    assert feed.languages == ["en", "fr"]


def test_get_trending_tags_feed_returns_trending_feed(mock_rw_session, mock_redis):
    from apps.api.feeds import TrendingTagsFeed

    feed = get_trending_tags_feed(rw=mock_rw_session, redis=mock_redis)

    assert isinstance(feed, TrendingTagsFeed)
