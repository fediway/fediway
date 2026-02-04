import pytest

# Skip entire module if feast is not available
pytest.importorskip("feast")

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
from fastapi import BackgroundTasks
from feast import FeatureService as FeastFeatureService

from shared.services.feature_service import FeatureService

ENTITIES = [{"status_id": 1}, {"status_id": 2}, {"status_id": 3}]
FEATURE_LIST = ["status__author_id", "status__engagements", "clip__embedding"]
FEATURE_SERVICE = MagicMock(spec=FeastFeatureService, name="test_service")


@pytest.fixture
def mock_online_features():
    df = pd.DataFrame(
        {
            "status_id": [1, 2, 3],
            "status__author_id": [5, 6, None],
            "status__engagements": [10, 20, None],
            "clip__embedding": [[0.5, 1.2], [0.4, 0.9], None],
        }
    )
    return df


@pytest.fixture
def mock_feature_store(mock_online_features):
    """Mock Feast FeatureStore with necessary methods"""
    mock_fs = MagicMock()

    # Mock get_feature_view
    mock_fv_status = MagicMock()
    mock_fv_status.entities = ["status_id"]
    mock_fv_status.tags = {"offline_store": "offline_store_status"}

    mock_fv_clip = MagicMock()
    mock_fv_clip.entities = ["status_id"]
    mock_fv_clip.tags = {}

    def get_feature_view(name):
        if name == "status":
            return mock_fv_status
        elif name == "clip":
            return mock_fv_clip
        else:
            return None

    mock_fs.get_feature_view.side_effect = get_feature_view

    # Mock get_online_features_async
    mock_online_response = MagicMock()
    mock_online_response.to_df.return_value = mock_online_features
    mock_fs.get_online_features_async = AsyncMock(return_value=mock_online_response)

    return mock_fs


@pytest.fixture
def feature_service(mock_feature_store):
    """FeatureService instance with mocked dependencies"""
    return FeatureService(
        feature_store=mock_feature_store,
        background_tasks=BackgroundTasks(),
        event_time=datetime.now(),
    )


# intest_to_offline_store tests


def test_ingest_successful(feature_service, mock_feature_store):
    status_id = 1
    author_id = 5
    engagements = 10
    embedding = [1.4, 0.3]
    event_time = 123

    features = pd.DataFrame([[author_id, engagements, embedding]], columns=FEATURE_LIST)
    feature_service.ingest_to_offline_store(
        features, [{"status_id": status_id}], event_time=event_time
    )

    # should be called once for status features
    feature_service.feature_store.write_to_offline_store.assert_called_once()

    kwargs = feature_service.feature_store.write_to_offline_store.call_args[1]

    assert "feature_view_name" in kwargs
    assert "df" in kwargs

    fv_name = kwargs["feature_view_name"]
    df = kwargs["df"]

    assert fv_name == "status"
    assert list(df.columns) == ["status_id", "author_id", "engagements", "event_time"]
    assert list(df.values[0]) == [
        status_id,
        author_id,
        engagements,
        event_time - (event_time % 60),
    ]


# get tests


@pytest.mark.asyncio
async def test_get_empty_features(feature_service):
    result = await feature_service.get(ENTITIES, [])
    assert result is None


@pytest.mark.asyncio
async def test_get_empty_entities(feature_service):
    result = await feature_service.get([], [f.replace("__", ":") for f in FEATURE_LIST])
    assert result is None


@pytest.mark.asyncio
async def test_get_with_feature_list_success(feature_service, mock_feature_store):
    feature_names = [f.replace("__", ":") for f in FEATURE_LIST]
    result = await feature_service.get(ENTITIES, feature_names)

    # Verify the call was made correctly
    mock_feature_store.get_online_features_async.assert_called_once_with(
        features=feature_names, entity_rows=ENTITIES, full_feature_names=True
    )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert "status__author_id" in result.columns
    assert "status__engagements" in result.columns


@pytest.mark.asyncio
async def test_get_with_feast_feature_service(feature_service, mock_feature_store):
    mock_feast_service = MagicMock(spec=FeastFeatureService)
    mock_feast_service.name = "test_service"

    mock_df = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]})

    mock_response = MagicMock()
    mock_response.to_df.return_value = mock_df
    mock_feature_store.get_online_features_async.return_value = mock_response

    result = await feature_service.get(ENTITIES, mock_feast_service)

    mock_feature_store.get_online_features_async.assert_called_once_with(
        features=mock_feast_service, entity_rows=ENTITIES, full_feature_names=True
    )

    assert isinstance(result, pd.DataFrame)


@pytest.mark.asyncio
async def test_get_with_cache_hit(feature_service):
    feature_service.cache = {
        "status_id": {
            "status__author_id": pd.Series([5, 6, 7], index=[1, 2, 3]),
            "status__engagements": pd.Series([10, 20, 30], index=[1, 2, 3]),
        }
    }

    result = await feature_service.get(ENTITIES, ["status__author_id", "status__engagements"])

    # Should not call online features since cache hit
    feature_service.feature_store.get_online_features_async.assert_not_called()

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert list(result.index) == [1, 2, 3]


@pytest.mark.asyncio
async def test_get_with_partial_cache_hit(feature_service, mock_feature_store):
    feature_service.cache = {
        "status_id": {
            "status__author_id": pd.Series([5, 6], index=[1, 2]),
            "status__engagements": pd.Series([10, 20], index=[1, 2]),
        }
    }

    # Mock response for missing entity
    mock_df = pd.DataFrame(
        {"status_id": [3], "status__author_id": [7], "status__engagements": [30]}
    )
    mock_response = MagicMock()
    mock_response.to_df.return_value = mock_df
    mock_feature_store.get_online_features_async.return_value = mock_response

    result = await feature_service.get(ENTITIES, ["status:author_id", "status:engagements"])

    # Should only call for missing entity
    mock_feature_store.get_online_features_async.assert_called_once_with(
        features=["status:author_id", "status:engagements"],
        entity_rows=[{"status_id": 3}],
        full_feature_names=True,
    )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3


# _remember tests


def test_remember_adds_features_to_empty_cache(feature_service):
    df = pd.DataFrame(
        {
            "status__author_id": [5, 6, 7],
            "status__engagements": [10, 20, 30],
        }
    )
    entities = [{"status_id": 1}, {"status_id": 2}, {"status_id": 3}]
    features = ["status:author_id", "status:engagements"]

    feature_service._remember(entities, df, features)

    assert "status_id" in feature_service.cache
    cached = feature_service.cache["status_id"]

    assert "status__author_id" in cached
    assert "status__engagements" in cached
    assert list(cached["status__author_id"].values) == [5, 6, 7]
    assert list(cached["status__author_id"].index) == [1, 2, 3]


def test_remember_merges_features(feature_service):
    # First remember call
    df1 = pd.DataFrame({"status__author_id": [5, 6]}, index=[0, 1])
    entities1 = [{"status_id": 1}, {"status_id": 2}]
    features = ["status:author_id"]

    feature_service._remember(entities1, df1, features)

    # Second remember call with one overlapping ID (1) and one new (3)
    df2 = pd.DataFrame({"status__author_id": [8, 9]}, index=[0, 1])
    entities2 = [{"status_id": 1}, {"status_id": 3}]

    feature_service._remember(entities2, df2, features)

    # Check merged cache
    cached = feature_service.cache["status_id"]["status__author_id"]
    assert list(cached.index) == [2, 1, 3] or list(cached.index) == [
        1,
        2,
        3,
    ]  # Duplicates dropped
    assert 1 in cached.index and 3 in cached.index


def test_remember_skips_when_cache_key_has_multiple_keys():
    feature_service = FeatureService(feature_store=MagicMock())

    df = pd.DataFrame({"status__author_id": [5]}, index=[0])
    entities = [{"status_id": 1, "user_id": 10}]  # multiple keys → skips
    features = ["status:author_id"]

    feature_service._remember(entities, df, features)

    assert feature_service.cache == {}  # Should remain empty


def test_remember_does_not_store_for_feature_service():
    feature_service = FeatureService(feature_store=MagicMock())
    df = pd.DataFrame({"some_feature": [1, 2, 3]})
    entities = [{"status_id": 1}, {"status_id": 2}, {"status_id": 3}]
    fs_obj = MagicMock(spec=FeastFeatureService)

    feature_service._remember(entities, df, fs_obj)

    assert feature_service.cache == {}  # Should remain empty
