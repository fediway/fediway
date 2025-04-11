
from sqlmodel import Session as DBSession, select
from fastapi import Request, BackgroundTasks, Depends

from modules.fediway.feed import Feed
from modules.fediway.sources import Source
from app.modules.sessions import Session
from app.modules.ranking import Ranker
from app.modules.models import Feed as FeedModel, Status, FeedRecommendation
from config import config

class FeedService():
    def __init__(self, 
                 name: str,
                 db: DBSession,
                 tasks: BackgroundTasks,
                 session: Session, 
                 sources: list[Source],
                 feed: Feed):
        self.name = name
        self.db = db
        self.tasks = tasks
        self.session = session
        self.sources = sources
        self.feed = feed

    def init(self):
        '''
        Initialize feed.
        '''

        feed = self.session.get(self.name)

        if feed is not None:
            # self.feed = feed
            return
        
        self.collect_sources_async()

        feed_model = FeedModel(
            session_id=self.session.id,
            ip=self.session.ipv4_address,
            user_agent=self.session.user_agent,
            name=self.name,
        )
        self.db.add(feed_model)
        self.db.commit()

        # store feed in session
        self.feed.id = feed_model.id
        self.session[self.name] = self.feed

        # wait until at least n candidates are collected from the sources
        # or timout
        self.feed.wait_for_candidates(self.max_n_per_source())

        # start ranking
        self.feed.rank_async()

        # wait until the ranker has finished
        self.feed.wait_for_ranker()

    def max_n_per_source(self):
        return config.fediway.feed_max_light_candidates // len(self.sources)

    def collect_sources_async(self):
        candidates = []
        max_n_per_source = self.max_n_per_source()

        # collect candidates from sources
        for source in self.sources:
            self.feed.collect_async(source, args=(max_n_per_source,))

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
        recommendations = self.feed.get_batch(n)

        # save recommendations
        self.tasks.add_task(self._save_recommendations, recommendations)

        return recommendations