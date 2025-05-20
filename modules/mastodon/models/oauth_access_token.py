from typing import List
from datetime import datetime
from sqlalchemy import Column, ARRAY, Integer, String
from sqlmodel import SQLModel, Field


class AccessToken(SQLModel, table=True):
    __tablename__ = "oauth_access_tokens"

    id: int = Field(primary_key=True)
    resource_owner_id: int = Field(foreign_key="users.id")
    token: str = Field()
    scopes: str = Field()
    revoked_at: datetime | None = Field()
