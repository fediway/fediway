import hashlib
import json
import uuid
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks, Request
from redis import Redis

from shared.utils import JSONEncoder
from shared.utils.logging import Timer, log_debug, log_error

if TYPE_CHECKING:
    from kafka import KafkaProducer

    from modules.fediway.feed import Feed
    from modules.fediway.feed.candidates import CandidateList
    from modules.fediway.feed.steps import RankingStep, SourcingStep
    from modules.mastodon.models import Account

CODE_VERSION = "0.1.0"


def _request_key(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}.{request.headers.get('User-Agent', '')}"


def _generate_feed_id(length: int = 8) -> str:
    return str(uuid.uuid4()).replace("-", "")[:length]


def _get_feed_key(request: Request, length: int = 32) -> str:
    return hashlib.sha256(_request_key(request).encode("utf-8")).hexdigest()[:length]


class FeedEngine:
    def __init__(
        self,
        kafka: "KafkaProducer",
        redis: Redis,
        request: Request,
        tasks: BackgroundTasks,
        account: "Account | None",
    ):
        self._kafka = kafka
        self._redis = redis
        self._request = request
        self._tasks = tasks
        self._account = account
        self._id = _generate_feed_id()
        self._key = _get_feed_key(request)

    async def run(
        self,
        feed: "Feed",
        flush: bool = False,
        cache_ttl: int | None = None,
        prefetch: bool = False,
        **kwargs,
    ) -> "CandidateList":
        with Timer() as t:
            if cache_ttl and not flush:
                cached = self._get_cached(feed, **kwargs)
                if cached is not None:
                    log_debug(
                        "Cache hit",
                        module="feed_engine",
                        feed=feed.__class__.__name__,
                    )
                    return cached

            if flush:
                feed.flush()

            results = await feed.execute(**kwargs)

            if cache_ttl:
                self._cache_results(feed, results, cache_ttl, **kwargs)

            if feed.pipeline:
                self._tasks.add_task(self._emit_metrics, feed, results)

            if prefetch and len(results) > 0:
                self._tasks.add_task(self._prefetch_next, feed, results, **kwargs)

        log_debug(
            "Feed executed",
            module="feed_engine",
            feed=feed.__class__.__name__,
            count=len(results),
            duration_ms=round(t.elapsed_ms, 2),
        )

        return results

    def _cache_key(self, feed: "Feed", **kwargs) -> str:
        kwarg_hash = hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()[:8]
        return f"feed_cache:{feed.__class__.__name__}:{self._key}:{kwarg_hash}"

    def _get_cached(self, feed: "Feed", **kwargs) -> "CandidateList | None":
        from modules.fediway.feed.candidates import CandidateList

        key = self._cache_key(feed, **kwargs)
        data = self._redis.get(key)
        if not data:
            return None

        try:
            state = json.loads(data)
            candidates = CandidateList(feed.entity)
            candidates.set_state(state)
            return candidates
        except Exception as e:
            log_error("Cache deserialization failed", module="feed_engine", error=str(e))
            return None

    def _cache_results(self, feed: "Feed", results: "CandidateList", ttl: int, **kwargs):
        key = self._cache_key(feed, **kwargs)
        try:
            state = results.get_state()
            self._redis.setex(key, ttl, json.dumps(state, cls=JSONEncoder))
        except Exception as e:
            log_error("Cache serialization failed", module="feed_engine", error=str(e))

    def _emit_metrics(self, feed: "Feed", results: "CandidateList"):
        from modules.fediway.feed.steps import RankingStep, SourcingStep

        try:
            pipeline = feed.pipeline
            if not pipeline:
                return

            feed_id = self._id
            run_id = str(uuid.uuid4())
            event_time = pipeline.event_time.isoformat()

            self._kafka.send(
                topic="feeds",
                key=feed_id,
                value={
                    "id": feed_id,
                    "user_agent": self._request.headers.get("User-Agent"),
                    "ip": self._request.client.host if self._request.client else None,
                    "account_id": self._account.id if self._account else None,
                    "name": feed.__class__.__name__,
                    "entity": feed.entity,
                    "event_time": event_time,
                },
            )

            self._kafka.send(
                topic="feed_pipeline_runs",
                key=run_id,
                value={
                    "id": run_id,
                    "feed_id": feed_id,
                    "iteration": pipeline.counter,
                    "duration_ns": sum(pipeline.get_durations()),
                    "code_version": CODE_VERSION,
                    "event_time": event_time,
                },
            )

            step_ids = {}
            durations = pipeline.get_durations()

            for idx, step in enumerate(pipeline.steps):
                step_id = str(uuid.uuid4())
                step_ids[idx] = step_id
                step_name = step.__class__.__name__ if hasattr(step, "__class__") else "lambda"

                self._kafka.send(
                    topic="feed_pipeline_steps",
                    key=step_id,
                    value={
                        "id": step_id,
                        "feed_id": feed_id,
                        "pipeline_run_id": run_id,
                        "name": step_name,
                        "params": step.get_params() if hasattr(step, "get_params") else {},
                        "duration_ns": durations[idx] if idx < len(durations) else 0,
                        "event_time": event_time,
                    },
                )

                if isinstance(step, SourcingStep):
                    self._emit_sourcing_metrics(feed_id, step_id, step, event_time)

                if isinstance(step, RankingStep):
                    self._emit_ranking_metrics(feed_id, run_id, step_id, step, event_time)

            for rec in results:
                rec_id = str(uuid.uuid4())
                self._kafka.send(
                    topic="feed_recommendations",
                    key=rec_id,
                    value={
                        "id": rec_id,
                        "feed_id": feed_id,
                        "pipeline_run_id": run_id,
                        "entity": feed.entity,
                        "entity_id": rec.id,
                        "sources": [s for s, _ in rec.sources],
                        "groups": [g for _, g in rec.sources],
                        "score": float(rec.score) if rec.score else 0.0,
                        "event_time": event_time,
                    },
                )

            self._kafka.flush()

        except Exception as e:
            log_error("Metrics emission failed", module="feed_engine", error=str(e))

    def _emit_sourcing_metrics(
        self,
        feed_id: str,
        step_id: str,
        step: "SourcingStep",
        event_time: str,
    ):
        durations = step.get_durations()
        counts = step.get_counts()
        sourced_candidates = step.get_sourced_candidates()

        for idx, (source, limit) in enumerate(step.sources):
            sourcing_run_id = str(uuid.uuid4())

            self._kafka.send(
                topic="feed_sourcing_runs",
                key=sourcing_run_id,
                value={
                    "id": sourcing_run_id,
                    "feed_id": feed_id,
                    "pipeline_step_id": step_id,
                    "source": source.id,
                    "candidates_limit": limit,
                    "candidates_count": counts[idx] if idx < len(counts) else 0,
                    "params": source.get_params() if hasattr(source, "get_params") else {},
                    "duration_ns": durations[idx] if idx < len(durations) else 0,
                    "event_time": event_time,
                },
            )

            if idx < len(sourced_candidates):
                for entity_id in sourced_candidates[idx]:
                    self._kafka.send(
                        topic="feed_candidate_sources",
                        key=f"{entity_id}:{sourcing_run_id}",
                        value={
                            "entity_id": step.group or "default",
                            "entity": entity_id,
                            "sourcing_run_id": sourcing_run_id,
                        },
                    )

    def _emit_ranking_metrics(
        self,
        feed_id: str,
        run_id: str,
        step_id: str,
        step: "RankingStep",
        event_time: str,
    ):
        ranking_run_id = str(uuid.uuid4())

        self._kafka.send(
            topic="feed_ranking_runs",
            key=ranking_run_id,
            value={
                "id": ranking_run_id,
                "feed_id": feed_id,
                "pipeline_run_id": run_id,
                "pipeline_step_id": step_id,
                "ranker": step.ranker.id if hasattr(step.ranker, "id") else "unknown",
                "params": step.ranker.get_params() if hasattr(step.ranker, "get_params") else {},
                "feature_retrieval_duration_ns": step.get_feature_retrieval_duration(),
                "ranking_duration_ns": step.get_ranking_duration(),
                "candidates_count": len(step.get_candidates()),
                "event_time": event_time,
            },
        )

    async def _prefetch_next(self, feed: "Feed", results: "CandidateList", **kwargs):
        if len(results) == 0:
            return

        try:
            last_id = results[-1].id
            await feed.execute(max_id=last_id, **kwargs)
        except Exception as e:
            log_error("Prefetch failed", module="feed_engine", error=str(e))
