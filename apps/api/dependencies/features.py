from fastapi import Request, Depends, BackgroundTasks

from shared.core.feast import feature_store
from shared.services.feature_service import FeatureService
from modules.fediway.rankers.kirby import KirbyFeatureService
from modules.mastodon.models import Account

from .auth import get_authenticated_account_or_fail
from config import config


def get_feature_service(request: Request, background_tasks: BackgroundTasks):
    if not hasattr(request.state, "features"):
        request.state.features = FeatureService(
            background_tasks=background_tasks,
            offline_store=config.feast.offline_store_enabled,
        )
    return request.state.features


def get_kirby_feature_service(
    account: Account = Depends(get_authenticated_account_or_fail),
    feature_service: FeatureService = Depends(get_feature_service),
):
    return KirbyFeatureService(
        feature_store=feature_store,
        feature_service=feature_service,
        account_id=account.id,
    )
