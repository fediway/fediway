
from datetime import datetime
from pydantic import BaseModel
from loguru import logger
import pandas as pd
import time

from app.modules.embed import Embedder
from app.modules.debezium import DebeziumBatchHandler

class StatusEmbeddings(BaseModel):
    status_id: int
    embeddings: list[float]
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
        embeddings = self.embedder([item['text'] for item in data])
        created_at = datetime.now()
        
        return [StatusEmbeddings(
            status_id=sid, 
            embeddings=emb,
            created_at=created_at
        ) for sid, emb in zip(status_ids, embeddings.tolist())]