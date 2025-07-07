import pytest
from unittest.mock import Mock, patch
from fastapi import Request, BackgroundTasks
from types import SimpleNamespace

from apps.api.dependencies.features import (
    get_feature_service,
    get_kirby_feature_service,
)


@patch("apps.api.dependencies.features.FeatureService")
@patch("apps.api.dependencies.features.config")
def test_get_feature_service_creates_feature_service_if_not_present(
    mock_config, mock_feature_service
):
    mock_request = Mock(spec=Request)
    mock_request.state = SimpleNamespace()
    mock_background_tasks = Mock(spec=BackgroundTasks)

    mock_config.feast.offline_store_enabled = True
    instance = mock_feature_service.return_value

    result = get_feature_service(mock_request, mock_background_tasks)

    mock_feature_service.assert_called_once_with(
        background_tasks=mock_background_tasks, offline_store=True
    )

    assert result == instance
    assert mock_request.state.features == result


@patch("apps.api.dependencies.features.FeatureService")
@patch("apps.api.dependencies.features.config")
def test_get_feature_service_creates_feature_service_with_offline_store_disabled(
    mock_config, mock_feature_service
):
    mock_request = Mock(spec=Request)
    mock_request.state = SimpleNamespace()
    mock_background_tasks = Mock(spec=BackgroundTasks)

    mock_config.feast.offline_store_enabled = False
    instance = mock_feature_service.return_value

    result = get_feature_service(mock_request, mock_background_tasks)

    mock_feature_service.assert_called_once_with(
        background_tasks=mock_background_tasks, offline_store=False
    )


def test_get_feature_service_returns_existing_instance():
    existing_feature_service = Mock()
    mock_request = Mock(spec=Request)
    mock_request.state = SimpleNamespace(features=existing_feature_service)
    mock_background_tasks = Mock(spec=BackgroundTasks)

    result = get_feature_service(mock_request, mock_background_tasks)

    assert result == existing_feature_service


@patch("apps.api.dependencies.features.KirbyFeatureService")
@patch("apps.api.dependencies.features.feature_store")
def test_get_kirby_feature_service_constructs_service(
    mock_feature_store, mock_kirby_feature_service
):
    mock_account = Mock()
    mock_account.id = "1234"
    mock_feature_service = Mock()

    instance = mock_kirby_feature_service.return_value

    result = get_kirby_feature_service(
        account=mock_account,
        feature_service=mock_feature_service,
    )

    mock_kirby_feature_service.assert_called_once_with(
        feature_store=mock_feature_store,
        feature_service=mock_feature_service,
        account_id="1234",
    )
    assert result == instance
