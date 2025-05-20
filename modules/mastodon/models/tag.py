from datetime import datetime
from sqlmodel import SQLModel, Field


class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    id: int = Field(primary_key=True)
    name: str = Field(nullable=False)
    usable: bool = Field(default=True)
    trendable: bool = Field(default=True)
    listable: bool = Field(default=True)
    created_at: datetime | None = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    reviewed_at: datetime = Field()
    requested_review_at: datetime = Field()
    last_status_at: datetime = Field()
    display_name: str = Field()


class StatusTag(SQLModel, table=True):
    __tablename__ = "statuses_tags"

    status_id: int = Field(primary_key=True)
    tag_id: str = Field(primary_key=True)
