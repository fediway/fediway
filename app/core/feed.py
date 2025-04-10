
import numpy as np
from fastapi import BackgroundTasks
from sqlmodel import Session as DBSession

from app.modules.feed import Feed
from app.modules.sources import Source
from app.modules.ranking import LightStatsRanker
from app.modules.models import Feed as FeedModel
from app.modules.sessions import Session
from app.settings import settings

light_ranker = LightStatsRanker()
heavy_ranker = lambda x: 1.0

def gather_sources(feed: Feed, sources: list[Source], db: Session) -> tuple[list[str], list[float]]:
    candidates = []
    scores = []
    max_n_per_source = settings.feed_max_light_candidates // len(sources)

    for source in sources:
        candidates += source.collect(max_n_per_source)
    
    scores = light_ranker.scores(candidates, db)
    
    meta = HeuristicMeta.for_candidates(candidates, db)
    
    return candidates, scores, meta

def get_samples(feed: Feed, 
                sources: list[Source], 
                tasks: BackgroundTasks, 
                db: Session):
    is_new = feed.is_empty()

    if is_new:
        feed.add_candidates('light', *gather_sources(feed, sources, db))

    return feed.sample('light', settings.feed_samples_page_size)