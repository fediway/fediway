from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column


class RankedEntity(SQLModel, table=True):
    __tablename__ = "ranked_entities"

    id: int = Field(primary_key=True)
    feed_id: int | None = Field(nullable=True)
    entity: str = Field(nullable=False)
    entity_id: int = Field(nullable=False)
    input: dict = Field(sa_column=Column(JSON()))
    score: float = Field(nullable=False)
    meta: dict = Field(sa_column=Column(JSON()))
