
from qdrant_client import QdrantClient, models
from datetime import datetime
from pydantic import BaseModel
from loguru import logger
import numpy as np
import time

import app.utils as utils
from app.modules.embed import Embedder
from app.modules.debezium import DebeziumBatchHandler, DebeziumEventHandler

class StatusEmbeddings(BaseModel):
    status_id: int
    embedding: list[float]
    created_at: datetime

class TextEmbeddingsEventHandler(DebeziumBatchHandler):
    def __init__(self, embedder: Embedder):
        self.embedder = embedder

    async def created(self, data: list[dict]):
        return self._embed(data)

    async def updated(self, old: list[dict], new: list[dict]):
        return self._embed(new)

    def _embed(self, data):
        status_ids = [item['status_id'] for item in data]
        with utils.duration("Generated text embeddings in {:.3f} seconds."):
            embeddings = self.embedder([item['text'] for item in data])
        created_at = datetime.now()
        
        return [StatusEmbeddings(
            status_id=sid, 
            embedding=emb,
            created_at=created_at
        ) for sid, emb in zip(status_ids, embeddings)]

class AccountEmbeddingsEventHandler(DebeziumEventHandler):
    client: QdrantClient

    def __init__(self, client: QdrantClient, collection: str):
        self.client = client
        self.collection = collection

    async def created(self, data: dict):
        self._push(data)

    async def updated(self, old: dict, new: dict):
        self._push(new)

    async def deleted(self, data: dict):
        pass

    def _push(self, data):
        if data.get('embeddings') is None:
            return
        
        if len(data['embeddings']) == 0:
            return
        
        embeddings = np.array(data['embeddings'])

        self.client.upsert(
            collection_name=self.collection,
            points=[models.PointStruct(
                id=data['account_id'],
                vector=np.mean(embeddings, axis=0).tolist()
            )]
        )

        logger.debug(f"Updated account embeddings for {data['account_id']} in '{self.collection}' collection.")