from datetime import datetime

import numpy as np
from pydantic import BaseModel
from qdrant_client import QdrantClient, models

from modules.fediway.embedding import Embedder, MultimodalEmbedder
from shared.utils.logging import Timer, log_debug


class StatusEmbeddings(BaseModel):
    status_id: int
    embedding: list[float]
    created_at: datetime


class TextEmbeddingsBatchHandler:
    def __init__(self, embedder: Embedder, min_chars: int = 4):
        self.embedder = embedder
        self.min_chars = min_chars

    def _filtered_texts(self, data: list[dict]):
        return [item["text"] for item in data if len(item["text"]) >= self.min_chars]

    def __call__(self, data):
        status_ids = [item["status_id"] for item in data]
        texts = self._filtered_texts(data)

        if len(texts) == 0:
            return []

        with Timer() as t:
            if isinstance(self.embedder, MultimodalEmbedder):
                embeddings = self.embedder.texts(texts)
            else:
                embeddings = self.embedder(texts)

        log_debug(
            "Generated text embeddings",
            module="embedding",
            count=len(texts),
            duration_ms=round(t.elapsed_ms, 2),
        )
        created_at = datetime.now()

        return [
            StatusEmbeddings(status_id=sid, embedding=emb, created_at=created_at)
            for sid, emb in zip(status_ids, embeddings)
        ]


class AccountEmbeddingsEventHandler:
    client: QdrantClient

    def __init__(self, client: QdrantClient, topic: str):
        self.client = client
        self.topic = topic

    def __call__(self, data):
        if data.get("embeddings") is None:
            return

        if len(data["embeddings"]) == 0:
            return

        # aggregate embeddings
        embeddings = np.array(data["embeddings"])
        embeddings = np.mean(embeddings, axis=0)

        self.client.upsert(
            collection_name=self.topic,
            points=[models.PointStruct(id=data["account_id"], vector=embeddings)],
        )

        log_debug(
            "Updated account embeddings",
            module="embedding",
            account_id=data["account_id"],
            collection=self.topic,
        )
