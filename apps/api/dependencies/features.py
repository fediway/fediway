from fastapi import Request

from shared.services.feature_service import FeatureService


def get_feature_service(request: Request):
    if not hasattr(request.state, "features"):
        request.state.features = FeatureService()
    return request.state.features
