from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.dependencies.auth import (
    get_authenticated_account,
    get_authenticated_account_or_fail,
)
from apps.api.dependencies.feeds import (
    get_feed_engine,
    get_home_feed,
    get_suggestions_feed,
    get_trending_statuses_feed,
    get_trending_tags_feed,
)
from apps.api.routes.api import router as api_router
from modules.fediway.feed.candidates import CandidateList
from shared.core.db import get_db_session
from shared.core.redis import get_redis
from shared.core.rw import get_rw_session


@pytest.fixture
def mock_account():
    account = MagicMock()
    account.id = 123
    return account


@pytest.fixture
def mock_db_session():
    session = MagicMock()

    def exec_side_effect(query):
        result = MagicMock()
        result.all.return_value = []
        return result

    session.exec = MagicMock(side_effect=exec_side_effect)
    return session


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get.return_value = None
    redis.setex.return_value = True
    return redis


@pytest.fixture
def mock_rw_session():
    return MagicMock()


@pytest.fixture
def mock_feed_engine():
    engine = MagicMock()

    async def mock_run(feed, state_key, flush=False, **kwargs):
        return CandidateList(feed.entity)

    engine.run = AsyncMock(side_effect=mock_run)
    return engine


@pytest.fixture
def mock_home_feed():
    feed = MagicMock()
    feed.entity = "status_id"
    return feed


@pytest.fixture
def mock_suggestions_feed():
    feed = MagicMock()
    feed.entity = "account_id"
    return feed


@pytest.fixture
def mock_trending_statuses_feed():
    feed = MagicMock()
    feed.entity = "status_id"
    return feed


@pytest.fixture
def mock_trending_tags_feed():
    feed = MagicMock()
    feed.entity = "tag_id"
    return feed


@pytest.fixture
def app(
    mock_account,
    mock_db_session,
    mock_redis,
    mock_rw_session,
    mock_feed_engine,
    mock_home_feed,
    mock_suggestions_feed,
    mock_trending_statuses_feed,
    mock_trending_tags_feed,
):
    application = FastAPI()
    application.include_router(api_router, prefix="/api")

    application.dependency_overrides[get_authenticated_account] = lambda: mock_account
    application.dependency_overrides[get_authenticated_account_or_fail] = lambda: mock_account
    application.dependency_overrides[get_db_session] = lambda: mock_db_session
    application.dependency_overrides[get_redis] = lambda: mock_redis
    application.dependency_overrides[get_rw_session] = lambda: mock_rw_session
    application.dependency_overrides[get_feed_engine] = lambda: mock_feed_engine
    application.dependency_overrides[get_home_feed] = lambda: mock_home_feed
    application.dependency_overrides[get_suggestions_feed] = lambda: mock_suggestions_feed
    application.dependency_overrides[get_trending_statuses_feed] = lambda: (
        mock_trending_statuses_feed
    )
    application.dependency_overrides[get_trending_tags_feed] = lambda: mock_trending_tags_feed

    return application


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def unauthenticated_app(
    mock_db_session,
    mock_redis,
    mock_rw_session,
    mock_feed_engine,
    mock_trending_statuses_feed,
    mock_trending_tags_feed,
):
    from fastapi import HTTPException, status

    def raise_unauthorized():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    application = FastAPI()
    application.include_router(api_router, prefix="/api")

    application.dependency_overrides[get_authenticated_account] = lambda: None
    application.dependency_overrides[get_authenticated_account_or_fail] = raise_unauthorized
    application.dependency_overrides[get_db_session] = lambda: mock_db_session
    application.dependency_overrides[get_redis] = lambda: mock_redis
    application.dependency_overrides[get_rw_session] = lambda: mock_rw_session
    application.dependency_overrides[get_feed_engine] = lambda: mock_feed_engine
    application.dependency_overrides[get_trending_statuses_feed] = lambda: (
        mock_trending_statuses_feed
    )
    application.dependency_overrides[get_trending_tags_feed] = lambda: mock_trending_tags_feed

    return application


@pytest.fixture
def unauthenticated_client(unauthenticated_app):
    return TestClient(unauthenticated_app, raise_server_exceptions=False)
