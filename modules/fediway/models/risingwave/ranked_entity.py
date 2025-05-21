from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column

class RankedEntity(SQLModel, table=True):
    __tablename__ = "ranked_entities"

    id: str = Field(primary_key=True)
    ranking_run_id: str = Field(nullable=False)
    entity: str = Field(nullable=False)
    entity_id: int = Field(nullable=False)
    features: dict = Field(sa_column=Column(JSONB()))
    score: float = Field(nullable=False)
    meta: dict = Field(sa_column=Column(JSONB()))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
