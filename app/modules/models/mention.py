
from typing import List
from datetime import datetime
from sqlalchemy import Column, ARRAY, Integer, String
from sqlmodel import SQLModel, Field
    
class Mention(SQLModel, table=True):
    __tablename__ = 'mentions'

    status_id: int = Field(primary_key=True)
    account_id: int = Field(primary_key=True)
    created_at: datetime | None = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    silent: bool = Field(default=False)