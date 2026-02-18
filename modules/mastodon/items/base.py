from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict


def _ensure_utc(v):
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


UTCDatetime = Annotated[datetime, BeforeValidator(_ensure_utc)]


class Item(BaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=True)
