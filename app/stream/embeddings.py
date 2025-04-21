
from pydantic import BaseModel
from loguru import logger
import pandas as pd
import time

from app.modules.embed import Embedder
from app.modules.debezium import DebeziumBatchHandler

class StatusEmbeddings(BaseModel):
    status_id: int
    embeddings: list[float]

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
        
        return [StatusEmbeddings(
            status_id=sid, 
            embeddings=emb
        ) for sid, emb in zip(status_ids, embeddings.tolist())]