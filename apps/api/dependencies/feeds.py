from sqlmodel import Session as DBSession
from fastapi import Request, Response, BackgroundTasks, Depends

from ..core.redis import redis
from ..services.feed_service import FeedService
from shared.core.db import get_db_session
from shared.services.feature_service import FeatureService

from .features import get_feature_service


def get_feed(
    request: Request,
    response: Response,
    tasks: BackgroundTasks,
    db: DBSession = Depends(get_db_session),
    feature_service: FeatureService = Depends(get_feature_service),
) -> FeedService:
    return FeedService(
        db=db,
        session=request.state.session,
        request=request,
        response=response,
        tasks=tasks,
        redis=redis,
        feature_service=feature_service,
    )
