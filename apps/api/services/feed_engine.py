import hashlib
import json
import uuid
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks, Request
from redis import Redis

from config import config
from shared.utils.logging import Timer, get_request_id, log_debug, log_error, log_warning

if TYPE_CHECKING:
    from kafka import KafkaProducer

    from modules.fediway.feed import Feed
    from modules.fediway.feed.candidates import CandidateList
    from modules.fediway.feed.steps import RankingStep, SourcingStep
    from modules.mastodon.models import Account

CODE_VERSION = "0.1.0"


def _generate_id(length: int = 8) -> str:
    return str(uuid.uuid4()).replace("-", "")[:length]


def get_request_state_key(request: Request, length: int = 16) -> str:
    """Generate a state key from request for anonymous feeds (trending, tags)."""
    host = request.client.host if request.client else "unknown"
    ua = request.headers.get("User-Agent", "")
    return hashlib.sha256(f"{host}.{ua}".encode("utf-8")).hexdigest()[:length]


class FeedEngine:
    def __init__(
        self,
        kafka: "KafkaProducer | None",
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
        self._feed_id = _generate_id()
        self._request_id = get_request_id()
        self._session_id: str | None = None

    def _get_session_key(self) -> str:
        """Redis key for session storage."""
        if self._account:
            return f"feed_session:account:{self._account.id}"
        return f"feed_session:guest:{get_request_state_key(self._request)}"

    def get_session_id(self) -> str:
        """Get or create a session ID, persisted in Redis for correlation."""
        if self._session_id is not None:
            return self._session_id

        key = self._get_session_key()
        ttl = config.fediway.feed_session_ttl

        try:
            existing = self._redis.get(key)
            if existing:
                self._session_id = existing.decode() if isinstance(existing, bytes) else existing
                # Refresh TTL on access
                self._redis.expire(key, ttl)
                return self._session_id
        except Exception as e:
            log_error("Failed to get session from Redis", module="feed_engine", error=str(e))

        # Generate new session
        self._session_id = _generate_id(12)

        try:
            self._redis.setex(key, ttl, self._session_id)
        except Exception as e:
            log_error("Failed to save session to Redis", module="feed_engine", error=str(e))

        return self._session_id

    def _get_feed_state_key(self, feed: "Feed", state_key: str) -> str:
        """Redis key for feed state storage."""
        return f"feed:{feed.__class__.__name__}:{state_key}"

    def _load_feed_state(self, feed: "Feed", state_key: str) -> None:
        """Load feed state from Redis."""
        key = self._get_feed_state_key(feed, state_key)
        try:
            data = self._redis.get(key)
            if data:
                state = json.loads(data)
                feed.set_state(state)
                log_debug(
                    "Feed state loaded",
                    module="feed_engine",
                    feed=feed.__class__.__name__,
                    remembered_count=len(feed._remembered),
                )
        except Exception as e:
            log_warning(f"Failed to load feed state: {e}", module="feed_engine")

    def _save_feed_state(self, feed: "Feed", state_key: str) -> None:
        """Save feed state to Redis."""
        key = self._get_feed_state_key(feed, state_key)
        try:
            state = feed.get_state()
            self._redis.setex(key, config.fediway.feed_session_ttl, json.dumps(state))
        except Exception as e:
            log_warning(f"Failed to save feed state: {e}", module="feed_engine")

    def _delete_feed_state(self, feed: "Feed", state_key: str) -> None:
        """Delete feed state from Redis."""
        key = self._get_feed_state_key(feed, state_key)
        try:
            self._redis.delete(key)
        except Exception as e:
            log_warning(f"Failed to delete feed state: {e}", module="feed_engine")

    async def run(
        self,
        feed: "Feed",
        state_key: str,
        flush: bool = False,
        prefetch: bool = True,
        **kwargs,
    ) -> "CandidateList":
        """Execute feed and return results.

        Args:
            feed: The feed instance to execute
            state_key: Unique key for state persistence (e.g., account_id or request hash)
            flush: Clear cached state before executing
            prefetch: Collect more candidates in background after returning

        After returning results, schedules background tasks:
        1. Emit metrics to Kafka (if pipeline exists)
        2. Prefetch more candidates for next request (if prefetch=True)

        The prefetch collects MORE candidates while user reads current page,
        so subsequent requests return instantly from cache.
        """
        with Timer() as t:
            if flush:
                feed.flush()
                self._delete_feed_state(feed, state_key)
            else:
                self._load_feed_state(feed, state_key)

            results = await feed.execute(**kwargs)

            self._save_feed_state(feed, state_key)

            if feed.pipeline and self._kafka:
                self._tasks.add_task(self._emit_metrics, feed, results)

            if prefetch and len(results) > 0:
                self._tasks.add_task(self._prefetch, feed, state_key)

        log_debug(
            "Feed executed",
            module="feed_engine",
            feed=feed.__class__.__name__,
            count=len(results),
            duration_ms=round(t.elapsed_ms, 2),
        )

        return results

    def _emit_metrics(self, feed: "Feed", results: "CandidateList"):
        from modules.fediway.feed.steps import RankingStep, SourcingStep

        try:
            pipeline = feed.pipeline
            if not pipeline:
                return

            feed_id = self._feed_id
            run_id = str(uuid.uuid4())
            event_time = pipeline.event_time.isoformat()

            self._kafka.send(
                topic="feeds",
                key=feed_id,
                value={
                    "id": feed_id,
                    "request_id": self._request_id,
                    "session_id": self.get_session_id(),
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

    async def _prefetch(self, feed: "Feed", state_key: str):
        """Collect more candidates in background for next request.

        This runs after returning results to the user. While they read
        the current page, we collect fresh candidates so subsequent
        requests return instantly from the cached _remembered list.
        """
        try:
            await feed.collect()
            self._save_feed_state(feed, state_key)
            log_debug(
                "Prefetch completed",
                module="feed_engine",
                feed=feed.__class__.__name__,
                remembered_count=len(feed._remembered),
            )
        except Exception as e:
            log_error("Prefetch failed", module="feed_engine", error=str(e))
