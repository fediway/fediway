
from sqlmodel import Session as DBSession, select
from fastapi import Request, BackgroundTasks, Depends

from app.core.db import get_db_session
from app.services.feed_service import FeedService
from app.services.status_features_service import StatusFeaturesService
from modules.fediway.sources import Source
from modules.fediway.feed import Feed, Heuristic, Sampler, TopKSampler

def get_status_feed(name: str, 
                    sources: callable,
                    heuristics: list[Heuristic] = [], 
                    sampler: Sampler = TopKSampler(),):
    
    def _inject(request: Request, 
                tasks: BackgroundTasks,
                db: DBSession = Depends(get_db_session),
                features: StatusFeaturesService = Depends(StatusFeaturesService),
                _sources: list[Source] = Depends(sources)):
        from app.core.feed import light_ranker, heavy_ranker

        return FeedService(
            name=name, 
            db=db, 
            session=request.state.session, 
            tasks=tasks,
            sources=_sources,
            feed=Feed(
                features=features,
                rankers=[(light_ranker, 100)],
                heuristics=heuristics,
                sampler=sampler
            ))
    
    return _inject