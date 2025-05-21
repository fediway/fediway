from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from modules.mastodon.models.status import Status

from .feed import Feed


class FeedRecommendation(SQLModel, table=True):
    __tablename__ = "feed_recommendations"

    id: int = Field(primary_key=True)
    feed_id: str = Field(nullable=False, foreign_key="feeds.id")
    status_id: str = Field(nullable=False, foreign_key="statuses.id")
    source: str = Field(nullable=False)
    score: float = Field(nullable=False)
    adjusted_score: float = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    feed: Feed = Relationship()
    status: Status = Relationship()
