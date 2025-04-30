
from sqlmodel import Session as DBSession, select
from fastapi import Request, BackgroundTasks, Depends, Response
from loguru import logger
import asyncio
import time

from modules.fediway.feed import Feed
from modules.fediway.sources import Source
from ..modules.sessions import Session
from modules.mastodon.models import Status
from modules.fediway.models.postgres import Feed as FeedModel, FeedRecommendation
import modules.utils as utils
from config import config

class FeedService():
    def __init__(self, 
                 name: str,
                 db: DBSession,
                 request: Request,
                 response: Response,
                 tasks: BackgroundTasks,
                 session: Session, 
                 sources: list[Source],
                 feed: Feed):
        self.session_key = f"feed.{name}.state"
        self.name = name
        self.db = db
        self.tasks = tasks
        self.request = request
        self.response = response
        self.session = session
        self.sources = sources
        self.feed = feed
    
    async def init(self):
        '''
        Initialize feed.
        '''

        state = self.session.get(self.session_key)

        if state is not None:
            self.feed.merge_dict(state)
            self._set_link_header()
            return

        await self.collect_sources()

        feed_model = FeedModel(
            session_id=self.session.id,
            ip=self.session.ipv4_address,
            user_agent=self.session.user_agent,
            name=self.name,
        )
        self.db.add(feed_model)
        self.db.commit()

        self.feed.id = feed_model.id
        self._set_link_header()

        # await collecting

    def _set_link_header(self):
        next_url = self.request.url.include_query_params(feed=self.feed.id)
        self.response.headers['link'] = f'<{next_url}>; rel="next"'

    def max_n_per_source(self):
        return config.fediway.feed_max_light_candidates // len(self.sources)

    async def collect_sources(self):
        jobs = []
        max_n_per_source = self.max_n_per_source()

        start = time.time()

        # collect candidates from sources
        for source in self.sources:
            logger.info(f"Started collecting candidates from {source}.")
            
            jobs.append(
                self.feed.collect(source, args=(max_n_per_source, ))
            )

        await asyncio.gather(*jobs)

        logger.info(f"Collected candidates in {int((time.time() - start) * 1000)} milliseconds.")

        await self.feed.rank()

    def _save_recommendations(self, recommendations):
        self.db.bulk_save_objects([FeedRecommendation(
            feed_id=self.feed.id,
            status_id=recommendation.item,
            source=recommendation.sources[0],
            score=float(recommendation.score),
            adjusted_score=float(recommendation.adjusted_score),
        ) for recommendation in recommendations])

        self.db.commit()

    def get_recommendations(self, n) -> list[int | str]:
        with utils.duration("Fetched recommendations in {:.3f} seconds."):
            recommendations = self.feed.get_batch(n)

        # save recommendations
        self.tasks.add_task(self._save_recommendations, recommendations)

        # load new candidates
        self.tasks.add_task(self.collect_sources)
        
        # save feed state in session
        self.session[self.session_key] = self.feed.to_dict()

        return recommendations