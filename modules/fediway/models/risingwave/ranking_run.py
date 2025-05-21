from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column


class RankingRun(SQLModel, table=True):
    __tablename__ = "ranking_runs"

    id: int = Field(primary_key=True)
    feed_id: int | None = Field(nullable=True)
    step_id: int = Field(nullable=True)
    duration_ns: int = Field(nullable=False)
    ranker: str = Field(nullable=False)
    params: dict = Field(sa_column=Column(JSON()))
    executed_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
