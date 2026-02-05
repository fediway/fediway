from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .status import Status


class StatusTopic(SQLModel, table=True):
    __tablename__ = "statuses_topics"

    status_id: str = Field(nullable=False, primary_key=True, foreign_key="statuses.id")
    topic_id: int = Field(nullable=False, primary_key=True, foreign_key="topics.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class Topic(SQLModel, table=True):
    __tablename__ = "topics"

    id: int = Field(primary_key=True)
    name: str = Field(nullable=False)
    display_name: str = Field(nullable=False)
    language: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    reviewed_at: datetime | None = Field(nullable=False)

    statuses: list["Status"] = Relationship(back_populates="topics", link_model=StatusTopic)
