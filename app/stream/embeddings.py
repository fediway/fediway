
from feast import FeatureStore
from feast.data_source import PushMode
from qdrant_client import QdrantClient, models
from datetime import datetime
from pydantic import BaseModel
from loguru import logger
import pandas as pd
import numpy as np
import time

from config import config
import app.utils as utils
from app.modules.embed import Embedder, MultimodalEmbedder
from app.modules.debezium import DebeziumBatchHandler, DebeziumEventHandler

class StatusEmbeddings(BaseModel):
    status_id: int
    embedding: list[float]
    created_at: datetime

class TextEmbeddingsBatchHandler(DebeziumBatchHandler):
    def __init__(self, embedder: Embedder, min_chars: int = 4):
        self.embedder = embedder
        self.min_chars = min_chars

    async def created(self, data: list[dict]):
        return self._embed(data)

    async def updated(self, old: list[dict], new: list[dict]):
        return self._embed(new)

    def _filtered_texts(self, data: list[dict]):
        return [item['text'] for item in data if len(item['text']) >= self.min_chars]

    def _embed(self, data):
        status_ids = [item['status_id'] for item in data]
        texts = self._filtered_texts(data)

        if len(texts) == 0:
            return []

        with utils.duration("Generated "+str(len(texts))+" text embeddings in {:.3f} seconds."):
            if isinstance(self.embedder, MultimodalEmbedder):
                embeddings = self.embedder.texts(texts)
            else:
                embeddings = self.embedder(texts)
        created_at = datetime.now()
        
        return [StatusEmbeddings(
            status_id=sid, 
            embedding=emb,
            created_at=created_at
        ) for sid, emb in zip(status_ids, embeddings)]

class AccountEmbeddingsEventHandler(DebeziumEventHandler):
    client: QdrantClient

    def __init__(self, client: QdrantClient, fs: FeatureStore, topic: str):
        self.fs = fs
        self.client = client
        self.topic = topic

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
        
        # aggregate embeddings
        embeddings = np.array(data['embeddings'])
        embeddings = np.mean(embeddings, axis=0)

        self.client.upsert(
            collection_name=self.topic,
            points=[models.PointStruct(
                id=data['account_id'],
                vector=embeddings
            )]
        )

        logger.info(f"Updated account embeddings for {data['account_id']} in '{self.topic}' collection.")

        # embeddings are only pushed to offline store (if enabled) for model training
        # qdrant serves as the online store for embeddings
        if config.feast.feast_offline_store_enabled:

            event_time = int(time.time())
            df = pd.DataFrame({
                'account_id': data['account_id'],
                'event_time': event_time,
                f"{self.topic}.embeddings": [embeddings],
            })

            self.fs.push(f"{self.topic}_stream", df, to=PushMode.OFFLINE)

            logger.info(f"Pushed '{self.topic}' for {data['account_id']} to offline feature store.")