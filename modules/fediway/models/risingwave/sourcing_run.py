from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column


class SourcingRun(SQLModel, table=True):
    __tablename__ = "sourcing_runs"

    id: int = Field(primary_key=True)
    feed_id: int | None = Field(nullable=True)
    step_id: int = Field(nullable=True)
    duration_ns: int = Field(nullable=False)
    group_name: str | None = Field(nullable=True)
    source: str = Field(nullable=False)
    candidates_limit: int = Field(nullable=False)
    candidates_count: int = Field(nullable=False)
    params: dict = Field(sa_column=Column(JSON()))
    executed_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
