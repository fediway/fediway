from fastapi import BackgroundTasks, Request

from config import config
from shared.services.feature_service import FeatureService


def get_feature_service(request: Request, background_tasks: BackgroundTasks):
    if not hasattr(request.state, "features"):
        request.state.features = FeatureService(
            background_tasks=background_tasks,
            offline_store=config.feast.offline_store_enabled,
        )
    return request.state.features
