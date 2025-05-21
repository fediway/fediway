import json
import uuid

import numpy as np
from fastapi import BackgroundTasks, Request, Response
from redis import Redis
from sqlmodel import Session as DBSession
from starlette.datastructures import URL

import modules.utils as utils
from config import config
from modules.fediway.feed.pipeline import Feed, PaginationStep
from modules.fediway.feed.sampling import Sampler, TopKSampler
from modules.fediway.heuristics import Heuristic
from modules.fediway.models.postgres import FeedRecommendation
from modules.fediway.rankers import Ranker
from modules.fediway.sources import Source
from shared.services.feature_service import FeatureService

from ..modules.sessions import Session


def _generate_feed_id(length: int = 8):
    return str(uuid.uuid4()).replace("-", "")[:length]


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyEncoder, self).default(obj)


class FeedService:
    feed: Feed

    def __init__(
        self,
        db: DBSession,
        request: Request,
        response: Response,
        tasks: BackgroundTasks,
        session: Session,
        redis: Redis,
        feature_service: FeatureService,
    ):
        self.r = redis
        self.db = db
        self.tasks = tasks
        self.request = request
        self.response = response
        self.session = session
        self.feature_service = feature_service
        self.pipeline = Feed(feature_service)

        self._next_offset = 0
        self.id = request.query_params.get("feed", _generate_feed_id())
        self.redis_key = f"feed:{self.id}"

    def name(self, name: str):
        self._name = name

        return self

    def source(self, source: Source, n: int):
        self.pipeline.source(source, n)

        return self

    def remember(self):
        self.pipeline.remember()

        return self

    def sources(self, sources: list[tuple[Source, int]]):
        self.pipeline.sources(sources)

        return self

    def select(self, entity: str):
        self.pipeline.select(entity)

        return self

    def rank(self, ranker: Ranker):
        self.pipeline.rank(ranker)

        return self

    def sample(self, n: int, sampler: Sampler = TopKSampler()):
        self.pipeline.sample(n, sampler)

        return self

    def paginate(self, limit: int, offset: int):
        self.pipeline.paginate(limit, offset)

        self._next_offset = limit + offset

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
        next_url = URL(
            f"{config.app.api_url}{self.request.url.path}"
        ).include_query_params(feed=self.id, offset=self._next_offset)

        self.response.headers["link"] = f'<{next_url}>; rel="next"'

    # def _save_recommendations(self, recommendations):
    #     self.db.bulk_save_objects(
    #         [
    #             FeedRecommendation(
    #                 feed_id=self.feed.id,
    #                 status_id=recommendation.item,
    #                 source=recommendation.sources[0],
    #                 score=float(recommendation.score),
    #                 adjusted_score=float(recommendation.adjusted_score),
    #             )
    #             for recommendation in recommendations
    #         ]
    #     )

    #     self.db.commit()

    async def _save_pipeline_run(self):
        pass
        # now = pd.to_datetime(datetime.now(config.app.timezone))

        # run = pd.DataFrame([{
        #     'feed_id': self.id,
        #     'index': self.pipeline.counter-1,
        #     'duration_ns': sum(self.pipeline.get_durations()),
        #     'executed_at': now
        # }])
        # steps = pd.DataFrame([{
        #     'feed_id': self.id,
        #     'run_index': self.pipeline.counter-1,
        #     'type': str(step.__class__.__name__),
        #     'duration_ns': duration_ns,
        #     'executed_at': now
        # } for step, duration_ns in zip(self.pipeline.steps, self.pipeline.get_durations())])
        
        # steps = pd.DataFrame([{
        #     'feed_id': self.id,
        #     'run_index': self.pipeline.counter-1,
        #     'type': str(step),
        #     'duration_ns': duration_ns,
        #     'executed_at': now
        # } for step, duration_ns in zip(self.pipeline.steps, self.pipeline.get_durations())])
        
        # recs = pd.DataFrame([{
        #     'feed_id': self.id,
        #     'entity': self.pipeline.entity,
        #     'entity_id': result,
        #     'created_at': now,
        # } for result in self.pipeline.results()])

        # with get_sender() as sender:
        #     sender.dataframe(run, table_name='pipeine_runs', at='executed_at')
        #     sender.dataframe(steps, table_name='pipeline_steps', at='executed_at')
        #     sender.dataframe(recs, table_name='feed_recommendations', at='created_at')

        # steps['duration_ns'] = steps['duration_ns'] / 1_000_000
        # print(steps)
        
    def _save_pipeline_state(self):
        state = self.pipeline.get_state()
        self.r.setex(
            self.redis_key, 
            config.session.session_ttl, 
            json.dumps(state, cls=NumpyEncoder)
        )

    async def _execute(self):
        with utils.duration("Executed pipeline in {:.3f} seconds."):
            await self.pipeline.execute()

        # store feed state in redis cache
        self._save_pipeline_state()

        # store pipeline execution data
        self.tasks.add_task(self._save_pipeline_run)

    def _load_cached(self):
        if not self.r.exists(self.redis_key):
            return

        state = json.loads(self.r.get(self.redis_key))
        self.pipeline.set_state(state)

    async def execute(self) -> list[int]:
        with utils.duration("Loaded recommendations in {:.3f} seconds."):
            self._load_cached()

            if self.pipeline.is_new():
                await self._execute()

            recommendations = self.pipeline.results()

            self._set_link_header()

            print(str(self.request.url), len(self.pipeline[-1]))

            # save recommendations
            # self.tasks.add_task(self._save_recommendations, recommendations)

            # load new candidates
            if not isinstance(self.pipeline[-1], PaginationStep) or len(
                self.pipeline[-1]
            ) < (self._next_offset + self.pipeline[-1].limit):
                self.tasks.add_task(self._execute)

            return recommendations
