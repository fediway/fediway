
from pydantic import BaseModel

class DebeziumPayload(BaseModel):
    op: str  # 'c', 'u', 'd', etc.
    before: dict | None
    after: dict | None
    source: dict

class DebeziumEvent(BaseModel):
    payload: DebeziumPayload