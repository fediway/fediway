from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class RankingRun(SQLModel, table=True):
    __tablename__ = "ranking_runs"

    id: int = Field(primary_key=True)
    feed_id: int | None = Field(nullable=True)
    rec_run_id: str = Field(nullable=False)
    rec_step_id: int = Field(nullable=False)
    feature_retrival_duration_ns: int = Field(nullable=False)
    ranking_duration_ns: int = Field(nullable=False)
    candidates_count: int = Field(nullable=False)
    ranker: str = Field(nullable=False)
    params: dict = Field(sa_column=Column(JSONB()))
    executed_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
