import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from fastapi import BackgroundTasks
from feast import FeatureService as FeastFeatureService
from unittest.mock import MagicMock, AsyncMock, patch

from modules.fediway.feed.features import Features
from shared.core.feast import feature_store
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
    assert list(df.values[0]) == [status_id, author_id, engagements, event_time]


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

    result = await feature_service.get(
        ENTITIES, ["status__author_id", "status__engagements"]
    )

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

    result = await feature_service.get(
        ENTITIES, ["status:author_id", "status:engagements"]
    )

    # Should only call for missing entity
    mock_feature_store.get_online_features_async.assert_called_once_with(
        features=["status:author_id", "status:engagements"],
        entity_rows=[{"status_id": 3}],
        full_feature_names=True,
    )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
