
from typing import List
from datetime import datetime
from sqlalchemy import Column, ARRAY, Integer, BigInteger, String
from sqlmodel import SQLModel, Field, Relationship

from .status import Status

class Feed(SQLModel, table=True):
    __tablename__ = 'feeds'

    id: int = Field(primary_key=True)
    session_id: str = Field(nullable=False)
    user_agent: str = Field(nullable=False)
    ip: str = Field(nullable=False)
    name: str = Field(nullable=False)
    name: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    user_id: datetime = Field(nullable=False)

class FeedRecommendation(SQLModel, table=True):
    __tablename__ = 'feed_recommendations'

    id: int = Field(primary_key=True)
    feed_id: str = Field(nullable=False, foreign_key="feeds.id")
    status_id: str = Field(nullable=False, foreign_key="statuses.id")
    source: str = Field(nullable=False)
    score: float = Field(nullable=False)
    adjusted_score: float = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    feed: Feed = Relationship()
    status: Status = Relationship(back_populates='recommendations')