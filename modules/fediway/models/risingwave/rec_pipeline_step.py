from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column


class RecPipelineStep(SQLModel, table=True):
    __tablename__ = "rec_pipeline_steps"

    id: int = Field(primary_key=True)
    feed_id: int | None = Field(nullable=True)
    run_id: int = Field(nullable=True)
    group_name: str = Field(nullable=False)
    name: str = Field(nullable=True)
    params: dict = Field(sa_column=Column(JSONB()))
    duration_ns: int = Field(nullable=False)
    executed_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
