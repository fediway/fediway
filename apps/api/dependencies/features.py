from fastapi import BackgroundTasks, Request

from config import config

try:
    from shared.services.feature_service import FeatureService
except ImportError:
    FeatureService = None


def get_feature_service(request: Request, background_tasks: BackgroundTasks):
    if FeatureService is None:
        raise ImportError("Feast is not installed. Install with: uv sync --extra features")
    if not hasattr(request.state, "features"):
        request.state.features = FeatureService(
            background_tasks=background_tasks,
            offline_store=config.feast.offline_store_enabled,
        )
    return request.state.features


def get_feature_service_optional(request: Request, background_tasks: BackgroundTasks):
    """Returns feature service if available, None otherwise."""
    if FeatureService is None:
        return None
    if not hasattr(request.state, "features"):
        request.state.features = FeatureService(
            background_tasks=background_tasks,
            offline_store=config.feast.offline_store_enabled,
        )
    return request.state.features
