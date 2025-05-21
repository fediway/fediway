from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class RecPipelineRun(SQLModel, table=True):
    __tablename__ = "rec_pipeline_runs"

    id: str = Field(primary_key=True)
    feed_id: str | None = Field(nullable=True)
    iteration: int = Field(nullable=False)
    duration_ns: int = Field(nullable=False)
    executed_at: datetime = Field(nullable=False)
