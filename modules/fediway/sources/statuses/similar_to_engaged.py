from datetime import datetime, timedelta

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, Range

from modules.fediway.feed.features import Features

from ..base import Source


class SimilarToEngagedSource(Source):
    def __init__(
        self,
        client: QdrantClient,
        account_id: int,
        feature_service: Features,
        language: str = "en",
        max_age=timedelta(days=3),
    ):
        self.client = client
        self.account_id = account_id
        self.language = language
        self.max_age = max_age
        self.feature_service = feature_service

    def group(self):
        return "similar_to_engaged"

    def name(self):
        return (
            f"similar_to_engaged[l={self.language},a={self.max_age.total_seconds()}]"
        )

    def collect(self, limit: int):
        status_ids = self.feature_service.get(
            entities=[{"account_id": self.account_id}],
            features=["latest_engaged_statuses:status_ids"],
        ).values[0, 0]

        if status_ids is None:
            return

        max_age = int((datetime.now() - self.max_age).timestamp())

        results = self.client.recommend(
            collection_name="status_embeddings",
            positive=status_ids,
            limit=limit,
            query_filter=Filter(
                must=FieldCondition(key="created_at", range=Range(gte=max_age))
            ),
        )

        for point in results:
            yield point.id
