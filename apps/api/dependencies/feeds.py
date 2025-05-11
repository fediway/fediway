
from sqlmodel import Session as DBSession, select
from fastapi import Request, Response, BackgroundTasks, Depends

from ..core.ranker import ranker
from ..services.feed_service import FeedService
from shared.core.db import get_db_session
from shared.core.feast import feature_store
from shared.services.feature_service import FeatureService
from modules.fediway.sources import Source
from modules.fediway.feed import Feed, Sampler, TopKSampler
from modules.fediway.heuristics import Heuristic

def get_feed(request: Request, 
             response: Response, 
             tasks: BackgroundTasks,
             db: DBSession = Depends(get_db_session)):

    return FeedService(
        db=db, 
        session=request.state.session, 
        request=request,
        response=response,
        tasks=tasks,
        feature_service=FeatureService(feature_store)
    )