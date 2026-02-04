import hashlib
import json
import uuid

import numpy as np
from fastapi import BackgroundTasks, Request
from kafka import KafkaProducer
from redis import Redis

from config import config
from modules.fediway.feed import Features
from modules.fediway.feed.pipeline import (
    CandidateList,
    Feed,
    PipelineStep,
    RankingStep,
    SourcingStep,
)
from modules.fediway.feed.sampling import Sampler, TopKSampler
from modules.fediway.heuristics import Heuristic
from modules.fediway.rankers import Ranker
from modules.fediway.sources import Source
from modules.mastodon.models import Account
from shared.services.feature_service import FeatureService
from shared.utils import JSONEncoder
from shared.utils.logging import Timer, log_debug, log_error


def request_key(request: Request):
    return f"{request.client.host}.{request.headers.get('User-Agent')}"


def _generate_feed_id(request: Request, length: int = 8):
    return str(uuid.uuid4()).replace("-", "")[:length]


def _get_feed_key(request: Request, length: int = 32):
    return hashlib.sha256(request_key(request).encode("utf-8")).hexdigest()[:length]


class FeedService:
    def __init__(
        self,
        kafka: KafkaProducer,
        request: Request,
        tasks: BackgroundTasks,
        redis: Redis,
        feature_service: FeatureService,
        account: Account | None,
    ):
        self.r = redis
        self.tasks = tasks
        self.kafka = kafka
        self.request = request
        self.feature_service = feature_service
        self.pipeline = Feed(feature_service)
        self.account = account
        self.key = _get_feed_key(request)
        self.id = _generate_feed_id(request)
        self._name = None

    @property
    def redis_key(self):
        return f"feed:{self._name}:{self.key}"

    @property
    def event_time(self):
        return int(self.feature_service.event_time.timestamp())

    def name(self, name: str):
        self._name = name

        return self

    def source(self, source: Source, n: int, group: str | None = None):
        self.pipeline.source(source, n, group)

        return self

    def remember(self):
        self.pipeline.remember()

        return self

    def sources(self, sources: list[tuple[Source, int]], group: str | None = None):
        self.pipeline.sources(sources, group)

        return self

    def select(self, entity: str):
        self.pipeline.select(entity)

        return self

    def unique(self):
        self.pipeline.unique()

        return self

    def rank(self, ranker: Ranker, feature_service: Features | None = None):
        self.pipeline.rank(ranker, feature_service)

        return self

    def sample(self, n: int, sampler: Sampler = TopKSampler()):
        self.pipeline.sample(n, sampler)

        return self

    def paginate(self, limit: int, offset: int = 0, max_id: int | None = None):
        self.pipeline.paginate(limit, offset, max_id)

        return self

    def heuristic(self, heuristic: Heuristic):
        self.pipeline.heuristic(heuristic)

        return self

    def diversify(self, by: str, penalty: float = 0.1):
        self.pipeline.diversify(by, penalty)

        return self

    def passthrough(self, callback):
        self.pipeline.passthrough(callback)

        return self

    def _ingest_feed(self):
        return self._send_kafka_message(
            topic="feeds",
            key=self.id,
            value={
                "id": self.id,
                "user_agent": self.request.headers.get("User-Agent"),
                "ip": self.request.client.host,
                "account_id": self.account.id if self.account else None,
                "name": self._name,
                "entity": self.pipeline.entity,
                "event_time": self.event_time,
            },
        )

    def _ingest_pipeline_run(self, run_id: str):
        return self._send_kafka_message(
            topic="feed_pipeline_runs",
            key=run_id,
            value={
                "id": run_id,
                "feed_id": self.id,
                "iteration": self.pipeline.counter - 1,
                "duration_ns": sum(self.pipeline.get_durations()),
                "code_version": config.app.code_version,
                "event_time": self.event_time,
            },
        )

    def _ingest_recommendations(self, run_id: str):
        futures = []

        for recommendation in self.pipeline.results():
            rec_id = str(uuid.uuid4())
            futures.append(
                self._send_kafka_message(
                    topic="feed_recommendations",
                    key=rec_id,
                    value={
                        "id": rec_id,
                        "feed_id": self.id,
                        "pipeline_run_id": run_id,
                        "entity": self.pipeline.entity,
                        "entity_id": recommendation.id,
                        "sources": [s for s, _ in recommendation.sources],
                        "groups": [g for _, g in recommendation.sources],
                        "score": np.clip(recommendation.score, 1e-10, None),
                        "event_time": self.event_time,
                    },
                )
            )

        return futures

    def _ingest_pipeline_steps(self, run_id: str):
        futures = []
        step_ids = [str(uuid.uuid4()) for _ in range(len(self.pipeline.steps))]

        for step_id, step, duration_ns in zip(
            step_ids, self.pipeline.steps, self.pipeline.get_durations()
        ):
            futures.append(
                self._send_kafka_message(
                    topic="feed_pipeline_steps",
                    key=step_id,
                    value={
                        "id": step_id,
                        "feed_id": self.id,
                        "pipeline_run_id": run_id,
                        "name": step.__class__.__name__,
                        "params": step.get_params() if isinstance(step, PipelineStep) else {},
                        "duration_ns": duration_ns,
                        "event_time": self.event_time,
                    },
                )
            )

        return step_ids, futures

    def _ingest_sourcing_runs(self, step_id: str, step: SourcingStep):
        futures = []

        for (source, limit), duration_ns, count, candidates in zip(
            step.sources,
            step.get_durations(),
            step.get_counts(),
            step.get_sourced_candidates(),
        ):
            sourcing_run_id = str(uuid.uuid4())

            futures.append(
                self._send_kafka_message(
                    topic="feed_sourcing_runs",
                    key=sourcing_run_id,
                    value={
                        "id": sourcing_run_id,
                        "feed_id": self.id,
                        "pipeline_step_id": step_id,
                        "params": source.get_params(),
                        "source": source.id,
                        "candidates_limit": limit,
                        "candidates_count": count,
                        "duration_ns": duration_ns,
                        "event_time": self.event_time,
                    },
                )
            )

            futures.extend(self._ingest_candidate_sources(sourcing_run_id, candidates))

        return futures

    def _ingest_candidate_sources(self, sourcing_run_id: str, candidates):
        futures = []

        for candidate in candidates:
            futures.append(
                self._send_kafka_message(
                    topic="feed_candidate_sources",
                    key=f"{sourcing_run_id},{candidate},{self.pipeline.entity}",
                    value={
                        "entity_id": candidate,
                        "entity": self.pipeline.entity,
                        "sourcing_run_id": sourcing_run_id,
                    },
                )
            )

        return futures

    def _ingest_ranking_runs(self, step_id: str, run_id: str, step: RankingStep):
        if step.get_ranking_duration() == 0:
            return []

        ranking_run_id = str(uuid.uuid4())

        return [
            self._send_kafka_message(
                topic="feed_ranking_runs",
                key=ranking_run_id,
                value={
                    "id": ranking_run_id,
                    "feed_id": self.id,
                    "pipeline_run_id": run_id,
                    "pipeline_step_id": step_id,
                    "ranker": step.ranker.id,
                    "ranker_params": step.ranker.get_params(),
                    "feature_retrieval_duration_ns": step.get_feature_retrieval_duration(),
                    "ranking_duration_ns": step.get_ranking_duration(),
                    "candidates_count": len(step.get_candidates()),
                    "event_time": self.event_time,
                },
            )
        ]

    async def _save_pipeline_run(self):
        futures = []

        futures.append(self._ingest_feed())

        run_id = str(uuid.uuid4())
        futures.append(self._ingest_pipeline_run(run_id))

        futures.extend(self._ingest_recommendations(run_id))

        step_ids, step_futures = self._ingest_pipeline_steps(run_id)
        futures.extend(step_futures)

        for step_id, step in zip(step_ids, self.pipeline.steps):
            if isinstance(step, SourcingStep):
                futures.extend(self._ingest_sourcing_runs(step_id, step))

            if isinstance(step, RankingStep):
                futures.extend(self._ingest_ranking_runs(step_id, run_id, step))

        self._await_kafka_futures(futures)

    def _await_kafka_futures(self, futures):
        for future in futures:
            try:
                future.get(timeout=10)
            except Exception as e:
                log_error("Kafka message delivery failed", module="feed", error=str(e))

        self.kafka.flush()

    def flush(self):
        self.r.delete(self.redis_key)

    def _save_state(self):
        state = {"id": self.id, "pipeline": self.pipeline.get_state()}

        self.r.setex(
            self.redis_key,
            config.fediway.feed_session_ttl,
            json.dumps(state, cls=JSONEncoder),
        )

    def _load_state(self):
        if not self.r.exists(self.redis_key):
            return

        state = json.loads(self.r.get(self.redis_key))

        if "pipeline" in state:
            self.pipeline.set_state(state["pipeline"])

        self.id = state.get("id", self.id)

    def _send_kafka_message(self, topic: str, key: str, value: dict):
        return self.kafka.send(topic=topic, key=key, value=value)

    async def _execute(self):
        with Timer() as t:
            await self.pipeline.execute()

        log_debug(
            "Executed pipeline",
            module="feed",
            name=self._name,
            duration_ms=round(t.elapsed_ms, 2),
        )

        # store feed state in redis cache
        self._save_state()

        # store pipeline execution data
        self.tasks.add_task(self._save_pipeline_run)

    async def execute(self) -> CandidateList:
        with Timer() as t:
            self._load_state()

            if self.pipeline.is_new():
                await self._execute()

            recommendations = self.pipeline.results()

            # load new candidates
            self.tasks.add_task(self._execute)

        log_debug(
            "Loaded recommendations",
            module="feed",
            name=self._name,
            count=len(recommendations),
            duration_ms=round(t.elapsed_ms, 2),
        )

        return recommendations
