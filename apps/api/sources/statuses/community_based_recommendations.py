from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import LookupLocation
from redis import Redis

from modules.fediway.sources.base import Source
from shared.utils.logging import log_warning


class CommunityBasedRecommendationsSource(Source):
    """Recommends content from communities matching user interests."""

    _id = "community_based_recommendations"
    _tracked_params = []

    def __init__(
        self,
        r: Redis,
        client: QdrantClient,
        account_id: int,
    ):
        self.r = r
        self.client = client
        self.account_id = account_id

    def _fetch_embeddings_version(self):
        return self.r.get("orbit:version")

    def collect(self, limit: int):
        version = self._fetch_embeddings_version().decode("utf8")

        try:
            results = self.client.query_points(
                collection_name=f"orbit_{version}_statuses",
                query=self.account_id,
                limit=limit,
                using="embedding",
                lookup_from=LookupLocation(
                    collection=f"orbit_{version}_consumers", vector="embedding"
                ),
            )
        except UnexpectedResponse as e:
            log_warning("Qdrant query failed", module="sources", error=str(e))
            return

        for point in results.points:
            yield point.id
