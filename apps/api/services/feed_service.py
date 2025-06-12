import json
import uuid
import hashlib

import numpy as np
from fastapi import BackgroundTasks, Request, Response
from faststream.confluent import KafkaBroker
from redis import Redis
from sqlmodel import Session as DBSession
from datetime import datetime

import modules.utils as utils
from config import config
from modules.mastodon.models import Account
from modules.fediway.feed import Features
from modules.fediway.feed.pipeline import (
    Feed,
    PaginationStep,
    SourcingStep,
    RankingStep,
)
from modules.fediway.feed.sampling import Sampler, TopKSampler
from modules.fediway.heuristics import Heuristic
from modules.fediway.models.risingwave import (
    Feed as FeedModel,
    Recommendation,
    RecPipelineRun,
    RecPipelineStep,
    RankedEntity,
    RankingRun,
    SourcingRun,
    RecommendationSource,
)
from modules.fediway.rankers import Ranker
from modules.fediway.sources import Source
from shared.services.feature_service import FeatureService

from ..modules.sessions import Session


def request_key(request: Request):
    return f"{request.client.host}.{request.headers.get('User-Agent')}"


def _generate_feed_id(request: Request, length: int = 8):
    return str(uuid.uuid4()).replace("-", "")[:length]


def _get_feed_key(request: Request, length: int = 32):
    return hashlib.sha256(request_key(request).encode("utf-8")).hexdigest()[:length]


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
    def __init__(
        self,
        db: DBSession,
        request: Request,
        tasks: BackgroundTasks,
        redis: Redis,
        feature_service: FeatureService,
        account: Account | None,
    ):
        self.r = redis
        self.db = db
        self.tasks = tasks
        self.request = request
        self.feature_service = feature_service
        self.pipeline = Feed(feature_service)
        self.account = account

        self.key = _get_feed_key(request)
        self.id = _generate_feed_id(request)

    def _redis_key(self):
        return f"feed:{self._name}:{self.key}"

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

    def rank(self, ranker: Ranker, feature_service: Features | None = None):
        self.pipeline.rank(ranker, feature_service)

        return self

    def sample(self, n: int, sampler: Sampler = TopKSampler()):
        self.pipeline.sample(n, sampler)

        return self

    def paginate(
        self, limit: int, offset: int | None = None, max_id: int | None = None
    ):
        self.pipeline.paginate(limit, offset, max_id)

        return self

    def heuristic(self, heuristic: Heuristic):
        self.pipeline.heuristic(heuristic)

        return self

    def diversify(self, by: str, penalty: float = 0.1):
        self.pipeline.diversify(by, penalty)

        return self

    async def _save_pipeline_run(self):
        now = datetime.now()

        self.db.merge(
            FeedModel(
                id=self.id,
                user_agent=self.request.headers.get("User-Agent"),
                ip=self.request.client.host,
                account_id=self.account.id if self.account else None,
                name=self._name,
                entity=self.pipeline.entity,
                created_at=now,
            )
        )

        run_id = str(uuid.uuid4())
        self.db.add(
            RecPipelineRun(
                id=run_id,
                feed_id=self.id,
                iteration=self.pipeline.counter - 1,
                duration_ns=sum(self.pipeline.get_durations()),
                executed_at=now,
            )
        )

        rec_step_ids = [str(uuid.uuid4()) for _ in range(len(self.pipeline.steps))]
        self.db.bulk_save_objects(
            [
                RecPipelineStep(
                    id=step_id,
                    feed_id=self.id,
                    run_id=run_id,
                    group_name=str(step.__class__.__name__),
                    name=str(step),
                    duration_ns=duration_ns,
                    executed_at=now,
                )
                for step_id, step, duration_ns in zip(
                    rec_step_ids, self.pipeline.steps, self.pipeline.get_durations()
                )
            ]
        )

        for step_id, step in zip(rec_step_ids, self.pipeline.steps):
            if not isinstance(step, SourcingStep):
                continue
            self.db.bulk_save_objects(
                [
                    SourcingRun(
                        id=str(uuid.uuid4()),
                        feed_id=self.id,
                        step_id=step_id,
                        group_name=source.group(),
                        source=source.name(),
                        candidates_limit=limit,
                        candidates_count=count,
                        duration_ns=duration_ns,
                        executed_at=now,
                    )
                    for (source, limit), duration_ns, count in zip(
                        step.sources, step.get_durations(), step.get_counts()
                    )
                ]
            )

        self.db.bulk_save_objects(
            [
                Recommendation(
                    id=str(uuid.uuid4()),
                    feed_id=self.id,
                    run_id=run_id,
                    entity=self.pipeline.entity,
                    entity_id=recommendation,
                    score=np.clip(score, 1e-10, None),
                    created_at=now,
                )
                for recommendation, score in zip(*self.pipeline.results())
            ]
        )

        for step_id, step in zip(rec_step_ids, self.pipeline.steps):
            if not isinstance(step, RankingStep):
                continue
            if step.get_ranking_duration() == 0:
                continue

            ranking_run_id = str(uuid.uuid4())
            self.db.add(
                RankingRun(
                    id=ranking_run_id,
                    feed_id=self.id,
                    rec_run_id=run_id,
                    rec_step_id=step_id,
                    ranker=step.ranker.name,
                    feature_retrival_duration_ns=step.get_feature_retrieval_duration(),
                    ranking_duration_ns=step.get_ranking_duration(),
                    candidates_count=len(step.get_candidates()),
                    executed_at=now,
                )
            )
            self.db.bulk_save_objects(
                [
                    RankedEntity(
                        id=str(uuid.uuid4()),
                        ranking_run_id=ranking_run_id,
                        entity=self.pipeline.entity,
                        entity_id=candidate,
                        features=features.to_dict(),
                        score=np.clip(score, 1e-10, None),
                        created_at=now,
                    )
                    for candidate, score, features in zip(
                        step.get_candidates(),
                        step.get_scores(),
                        step.get_features().iloc,
                    )
                ]
            )

        self.db.commit()

    def flush(self):
        self.r.delete(self._redis_key())

    def _save_state(self):
        state = {"id": self.id, "pipeline": self.pipeline.get_state()}

        self.r.setex(
            self._redis_key(),
            config.fediway.feed_session_ttl,
            json.dumps(state, cls=NumpyEncoder),
        )

    def _load_state(self):
        if not self.r.exists(self._redis_key()):
            return

        state = json.loads(self.r.get(self._redis_key()))
        if "pipeline" in state:
            self.pipeline.set_state(state["pipeline"])
        self.id = state.get("id", self.id)

    async def _execute(self):
        with utils.duration("Executed pipeline in {:.3f} seconds."):
            await self.pipeline.execute()

        # store feed state in redis cache
        self._save_state()

        # store pipeline execution data
        self.tasks.add_task(self._save_pipeline_run)

    async def execute(self) -> list[int]:
        with utils.duration("Loaded recommendations in {:.3f} seconds."):
            self._load_state()

            if self.pipeline.is_new():
                await self._execute()

            recommendations, _ = self.pipeline.results()

            print(
                str(self.request.url),
                len(self.pipeline[-1]),
                len(recommendations),
                self.pipeline[-1].offset,
                self.pipeline[-1].max_id,
                self.pipeline.counter,
            )

            # load new candidates
            self.tasks.add_task(self._execute)

            return recommendations
