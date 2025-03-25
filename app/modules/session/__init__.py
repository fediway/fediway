from uuid import uuid4
from fastapi import FastAPI, Request, Response
from cachetools import TLRUCache
import threading
import time

class Session():
    data: dict = {}

    def __init__(self, id, ipv4_address, user_agent):
        self.id = id
        self.ipv4_address = ipv4_address
        self.user_agent = user_agent
        self.data = {}

    @classmethod
    def from_request(cls, request: Request, id: str = uuid4()): 
        return cls(
            id=str(id),
            ipv4_address=request.client.host,
            user_agent=request.headers.get('User-Agent'),
        )

    def get(self, key, default = None):
        return self.data.get(key, default)

    def __setitem__(self, key, value):
        self.data[key] = value

class SessionManager():
    def __init__(self, maxsize: int = 10000, max_age_in_seconds: int = 600):
        self.cache = TLRUCache(
            maxsize=maxsize,
            ttu=lambda key, value, now: now + max_age_in_seconds,
            timer=time.monotonic
        )
        self.lock = threading.Lock()

    def get_session(self, session_id: str):
        with self.lock:
            data = self.cache.get(session_id)
        return data

    def create_session(self, session_id, data):
        with self.lock:
            self.cache[session_id] = data

    def update(self, session_id, data):
        with self.lock:
            self.cache[session_id] = data