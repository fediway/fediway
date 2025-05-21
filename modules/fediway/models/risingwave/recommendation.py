from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class Recommendation(SQLModel, table=True):
    __tablename__ = "recommendations"

    id: int = Field(primary_key=True)
    feed_id: int | None = Field(nullable=True)
    entity: str = Field()
    entity_id: str = Field(nullable=False)
    score: float = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
