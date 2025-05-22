from fastapi import BackgroundTasks, Depends, Request, Response
from sqlmodel import Session as DBSession

from modules.mastodon.models import Account

from shared.core.rw import get_rw_session
from shared.services.feature_service import FeatureService

from ..core.redis import redis
from ..services.feed_service import FeedService
from .features import get_feature_service
from .auth import get_authenticated_account


def get_feed(
    request: Request,
    response: Response,
    tasks: BackgroundTasks,
    db: DBSession = Depends(get_rw_session),
    feature_service: FeatureService = Depends(get_feature_service),
    account: Account | None = Depends(get_authenticated_account),
) -> FeedService:
    return FeedService(
        db=db,
        session=request.state.session,
        request=request,
        response=response,
        tasks=tasks,
        redis=redis,
        feature_service=feature_service,
        account=account,
    )
