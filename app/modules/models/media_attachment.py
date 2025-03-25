
from typing import Annotated, Union
from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field, Relationship

class MediaAttachment(SQLModel, table=True):
    __tablename__ = 'media_attachments'

    id: int = Field(primary_key=True)
    type: int = Field(nullable=False)
    status_id: int = Field(foreign_key="statuses.id")
    account_id: int = Field(foreign_key="accounts.id")
    description: str = Field()
    preview_url: str | None = Field()
    text_url: str | None = Field()
    remote_url: str | None = Field()
    blurhash: str | None = Field()
    aspect_ratio: float | None = Field()
    duration_seconds: int | None = Field()
    fps: int | None = Field()

    # file_name: str | None = Field()
    # file_content_type: str | None = Field()
    # file_size: str | None = Field()
    file_meta: dict = Field(sa_column=Column(JSON()))

    # thumbnail_file_name: str = Field()
    # thumbnail_content_type: str = Field()
    # thumbnail_file_size: str = Field()
    # thumbnail_content_type: str = Field()
    # thumbnail_remote_url: str = Field()

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    status: "Status" = Relationship(back_populates='media_attachments')