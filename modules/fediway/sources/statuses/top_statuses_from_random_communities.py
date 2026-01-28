
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import QueryRequest, SparseVector
from redis import Redis

from ..base import Source


class TopStatusesFromRandomCommunitiesSource(Source):
    """
    Queryies top statuses for random communities.

    This source can be used as an effective cold start to show new users diverse
    content to find out what they like more quickly.
    """

    def __init__(self, r: Redis, client: QdrantClient, batch_size: int = 5):
        self.r = r
        self.client = client
        self.batch_size = batch_size

    def get_params(self):
        return {
            "batch_size": self.batch_size,
        }

    def name(self):
        return "top_statuses_from_random_communities"

    def _fetch_embeddings_version(self) -> str:
        return self.r.get("orbit:version").decode("utf8")

    def _fetch_embeddings_dim(self) -> int:
        return int(self.r.get("orbit:dim").decode("utf8"))

    def collect(self, limit: int):
        dim = self._fetch_embeddings_dim()
        version = self._fetch_embeddings_version()

        n_communities = limit // self.batch_size

        # sample random communities
        communities = np.random.choice(np.arange(dim), size=min(dim, n_communities), replace=False)

        # create sparse vectors representing the communities
        vectors = [SparseVector(indices=[c], values=[1.0]) for c in communities]

        queries = [
            QueryRequest(query=vector, limit=self.batch_size, using="embedding")
            for vector in vectors
        ]

        # query batch of items for each community
        batches = self.client.query_batch_points(
            collection_name=f"orbit_{version}_statuses",
            requests=queries,
        )

        for batch in batches:
            for status in batch.points:
                yield status.id
