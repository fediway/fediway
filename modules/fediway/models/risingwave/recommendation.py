from datetime import datetime

from sqlmodel import Field, SQLModel


class Recommendation(SQLModel, table=True):
    __tablename__ = "recommendations"

    id: str = Field(primary_key=True)
    feed_id: str | None = Field(nullable=True)
    rec_run_id: str = Field(nullable=False)
    entity: str = Field()
    entity_id: str = Field(nullable=False)
    score: float = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
