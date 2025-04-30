
from sqlmodel import Session as DBSession, select
from fastapi import Request, Response, BackgroundTasks, Depends

from ..core.ranker import ranker
from ..services.feed_service import FeedService
from shared.core.db import get_db_session
from shared.services.features_service import FeaturesService
from modules.fediway.sources import Source
from modules.fediway.feed import Feed, Sampler, TopKSampler
from modules.fediway.heuristics import Heuristic

def get_status_feed(name: str, 
                    sources: callable,
                    heuristics: list[Heuristic] = [], 
                    sampler: Sampler = TopKSampler(),):
    
    def _inject(request: Request, 
                response: Response, 
                tasks: BackgroundTasks,
                db: DBSession = Depends(get_db_session),
                _sources: list[Source] = Depends(sources)):

        return FeedService(
            name=name, 
            db=db, 
            session=request.state.session, 
            request=request,
            response=response,
            tasks=tasks,
            sources=_sources,
            feed=Feed(
                features=FeaturesService(),
                rankers=[(ranker, 100)],
                heuristics=heuristics,
                sampler=sampler
            ))
    
    return _inject