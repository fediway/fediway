
from datetime import timedelta, datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, Range

from modules.fediway.feed.features import Features
from ..base import Source

class SimilarToFavourited(Source):
    def __init__(
        self, 
        client: QdrantClient, 
        account_id: int, 
        feature_service: Features,
        language: str = 'en', 
        max_age = timedelta(days=3)
    ):
        self.client = client
        self.account_id = account_id
        self.language = language
        self.max_age = max_age
        self.feature_service = feature_service

    def collect(self, limit: int):
        favourites = self.feature_service.get(
            entities=[{'account_id': self.account_id}],
            features=['account_favourites:favourites']
        )[0][0]

        max_age = int((datetime.now() - self.max_age).timestamp())

        results = self.client.recommend(
            collection_name="status_embeddings",
            positive=favourites,
            limit=limit,
            query_filter=Filter(
                must=FieldCondition(
                    key="created_at",
                    range=Range(gte=max_age)
                )
            )
        )

        for point in results:
            yield point.id