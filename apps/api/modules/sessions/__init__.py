from uuid import uuid4
from fastapi import FastAPI, Request, Response
from cachetools import TLRUCache
from aioredis import Redis
import numpy as np
import hashlib
import threading
import json
import time


def request_key(request: Request):
    return hashlib.sha256(
        f"{request.client.host}.{request.headers.get('User-Agent')}".encode("utf-8")
    ).hexdigest()


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyEncoder, self).default(obj)


class Session:
    data: dict = {}

    def __init__(self, id, key, ipv4_address, user_agent, data={}):
        self.id = id
        self.key = key
        self.ipv4_address = ipv4_address
        self.user_agent = user_agent
        self.data = {}
        self._modified = False

    @classmethod
    def from_request(cls, request: Request, id: str = uuid4()):
        return cls(
            id=str(id),
            key=request_key(request),
            ipv4_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
        )

    @classmethod
    def from_dict(cls, id: str, data):
        return cls(id, data["ipv4_address"], data[""])

    def get(self, key, default=None):
        return self.data.get(key, default)

    def has_changed(self):
        return self._modified

    def __setitem__(self, key, value):
        self.data[key] = value
        self._modified = True

    def __delitem__(self, key: str) -> None:
        del self.data[key]
        self._modified = True


class SessionManager:
    def __init__(
        self,
        redis_prefix: str = "session",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_name: str | int = 0,
        redis_pass: str | None = None,
        maxsize: int = 10_000,
        ttl: int = 600,
    ):
        self.ttl = ttl
        self.prefix = redis_prefix
        self.redis = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_name,
            password=redis_pass,
            decode_responses=True,
        )

    async def get(self, request: Request):
        key = request_key(request)
        if not await self.redis.exists(f"{self.prefix}.{key}"):
            return
        data = await self.redis.get(f"{self.prefix}.{key}")

        if data is not None:
            data = json.loads(data)
        else:
            data = {}

        session = Session.from_request(request)
        session.data = data

        return session

    async def update(self, session: Session):
        if not session.has_changed():
            return

        await self.redis.set(
            f"{self.prefix}.{session.key}",
            json.dumps(session.data, cls=NumpyEncoder),
            ex=self.ttl,
        )
