
from sqlmodel import Session as DBSession, select
from fastapi import Request, BackgroundTasks, Depends, Response
from loguru import logger
import asyncio
import time

from modules.fediway.feed.pipeline import Feed
from modules.fediway.feed.sampling import Sampler, TopKSampler
from modules.fediway.sources import Source
from modules.fediway.rankers import Ranker
from modules.fediway.heuristics import Heuristic, DiversifyHeuristic
from shared.services.feature_service import FeatureService
from ..modules.sessions import Session
from modules.mastodon.models import Status
from modules.fediway.models.postgres import Feed as FeedModel, FeedRecommendation
import modules.utils as utils
from config import config

class FeedService():
    feed: Feed

    def __init__(self, 
                 name: str,
                 db: DBSession,
                 request: Request,
                 response: Response,
                 tasks: BackgroundTasks,
                 session: Session, 
                 feature_service: FeatureService):
        self.session_key = f"feed.{name}.state"
        self.name = name
        self.db = db
        self.tasks = tasks
        self.request = request
        self.response = response
        self.session = session
        self.feature_service = feature_service
        self.pipeline = Feed(feature_service)

        self._set_link_header()

    def source(self, source: Source, n: int):
        self.pipeline.source(source, n)

        return self

    def sources(self, sources: list[tuple[Source, int]]):
        self.pipeline.sources(sources)

        return self

    def rank(self, ranker: Ranker):
        self.pipeline.rank(ranker)

        return self

    def sample(self, n: int, sampler: Sampler = TopKSampler()):
        self.pipeline.sample(n, sampler)

        return self

    def paginate(self, limit: int, offset: int):
        self.pipeline.paginate(limit, offset)

        return self

    def heuristic(self, heuristic: Heuristic):
        self.pipeline.heuristic(heuristic)

        return self

    def diversify(self, by: str, penalty: float = 0.1):
        self.pipeline.diversify(by, penalty)

        return self
    
    # async def init(self):
    #     '''
    #     Initialize feed.
    #     '''

    #     state = self.session.get(self.session_key)

    #     # if state is not None:
    #     #     # self.feed.merge_dict(state)
    #     #     self._set_link_header()
    #     #     return

    #     await self.collect_sources()

    #     feed_model = FeedModel(
    #         session_id=self.session.id,
    #         ip=self.session.ipv4_address,
    #         user_agent=self.session.user_agent,
    #         name=self.name,
    #     )
    #     self.db.add(feed_model)
    #     self.db.commit()

    #     self.feed.id = feed_model.id
    #     self._set_link_header()

    #     # await collecting

    def _set_link_header(self):
        next_url = self.request.url
        
        # .include_query_params(
        #     feed=self.feed.id,
        #     # offset=
        # )

        self.response.headers['link'] = f'<{next_url}>; rel="next"'

    def _save_recommendations(self, recommendations):
        self.db.bulk_save_objects([FeedRecommendation(
            feed_id=self.feed.id,
            status_id=recommendation.item,
            source=recommendation.sources[0],
            score=float(recommendation.score),
            adjusted_score=float(recommendation.adjusted_score),
        ) for recommendation in recommendations])

        self.db.commit()

    async def execute(self) -> list[int]:
        if self.pipeline.is_empty():
            with utils.duration("Executed pipeline in {:.3f} seconds."):
                await self.pipeline.execute()
            
        recommendations = self.pipeline.results()

        # save recommendations
        # self.tasks.add_task(self._save_recommendations, recommendations)

        # load new candidates
        self.tasks.add_task(self.pipeline.execute)
        
        # save feed state in session
        # self.session[self.session_key] = self.feed.to_dict()

        return recommendations