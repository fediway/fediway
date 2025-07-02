from redis import Redis
from datetime import datetime, timedelta
import asyncio

from qdrant_client import QdrantClient
from qdrant_client.models import LookupLocation

from modules.fediway.feed.features import Features

from ..base import Source


class CommunityBasedRecommendationsSource(Source):
    def __init__(
        self,
        r: Redis,
        client: QdrantClient,
        account_id: int,
    ):
        self.r = r
        self.client = client
        self.account_id = account_id

    def name(self):
        return f"community_based_recommendations"

    def _fetch_embeddings_version(self):
        return self.r.get("orbit:version")

    def collect(self, limit: int):
        version = self._fetch_embeddings_version().decode("utf8")

        results = self.client.recommend(
            collection_name=f"orbit_{version}_statuses",
            positive=[self.account_id],
            limit=limit,
            using="embedding",
            lookup_from=LookupLocation(
                collection=f"orbit_{version}_consumers", vector="embedding"
            ),
        )

        for point in results:
            yield point.id
