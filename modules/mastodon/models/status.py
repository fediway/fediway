from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, ARRAY, Integer
from sqlmodel import SQLModel, Field, Relationship

from .account import Account
from .media_attachment import MediaAttachment
from .preview_card import PreviewCard, PreviewCardStatus
from .topic import Topic, StatusTopic
from .favourite import Favourite


class StatusStats(SQLModel, table=True):
    __tablename__ = "status_stats"

    status_id: int = Field(primary_key=True, foreign_key="statuses.id")
    replies_count: int = Field(default=0)
    reblogs_count: int = Field(default=0)
    favourites_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    status: "Status" = Relationship(
        back_populates="stats", sa_relationship_kwargs={"uselist": False}
    )


class Status(SQLModel, table=True):
    __tablename__ = "statuses"

    id: int = Field(primary_key=True)
    uri: int | None = Field()
    url: int | None = Field()
    sensitive: bool = Field(default=False)
    visibility: int = Field()
    text: str = Field()
    spoiler_text: str = Field()
    created_at: datetime | None = Field()
    edited_at: datetime | None = Field()
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted_at: datetime | None = Field()
    # last_processed_at: datetime | None = Field(nullable=True)
    in_reply_to_id: int | None = Field()
    reblog_of_id: int | None = Field(default=None, foreign_key="statuses.id")
    language: str | None = Field()
    account_id: int = Field(nullable=False, foreign_key="accounts.id")
    in_reply_to_account_id: int | None = Field()
    ordered_media_attachment_ids: List[int] = Field(sa_column=Column(ARRAY(Integer)))

    favourites: list[Favourite] = Relationship(back_populates="status")
    account: Account | None = Relationship(back_populates="statuses")
    stats: StatusStats = Relationship(
        back_populates="status", sa_relationship_kwargs={"uselist": False}
    )
    media_attachments: list[MediaAttachment] = Relationship(back_populates="status")
    preview_card: PreviewCard = Relationship(
        back_populates="statuses", link_model=PreviewCardStatus
    )
    topics: list[Topic] = Relationship(
        back_populates="statuses", link_model=StatusTopic
    )
    # reblogs: list["Status"] = Relationship(back_populates="reblog")
    reblog: Optional["Status"] = Relationship(
        sa_relationship_kwargs={
            "remote_side": "Status.id",
            "foreign_keys": "Status.reblog_of_id",
            "uselist": False,
        }
    )

    @classmethod
    def select_by_ids(cls, ids):
        from sqlmodel import select
        from sqlalchemy.orm import selectinload

        return (
            select(cls)
            .options(selectinload(cls.account).subqueryload(Account.stats))
            .options(selectinload(cls.preview_card))
            .options(selectinload(cls.stats))
            .options(
                (
                    selectinload(cls.reblog)
                    .options(selectinload(cls.media_attachments))
                    .options(selectinload(cls.stats))
                    .options(selectinload(cls.preview_card))
                )
            )
            .options(selectinload(cls.media_attachments))
            .where(cls.id.in_(ids))
        )
