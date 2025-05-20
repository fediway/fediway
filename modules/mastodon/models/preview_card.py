from typing import List
from datetime import datetime
from sqlalchemy import Column, ARRAY, Integer, BigInteger, String
from sqlmodel import SQLModel, Field, Relationship


class PreviewCardStatus(SQLModel, table=True):
    __tablename__ = "preview_cards_statuses"

    preview_card_id: int = Field(
        nullable=False, primary_key=True, foreign_key="preview_cards.id"
    )
    status_id: str = Field(nullable=False, primary_key=True, foreign_key="statuses.id")


class PreviewCard(SQLModel, table=True):
    __tablename__ = "preview_cards"

    id: int = Field(primary_key=True)
    url: str = Field(nullable=False, default="")
    title: str = Field(nullable=False, default="")
    description: str = Field(nullable=False, default="")
    type: int = Field(nullable=False, default=0)
    html: str = Field(nullable=False, default="")
    author_name: str = Field(nullable=False, default="")
    author_url: str = Field(nullable=False, default="")
    provider_url: str = Field(nullable=False, default="")
    provider_name: str = Field(nullable=False, default="")
    width: int = Field(nullable=False, default=0)
    height: int = Field(nullable=False, default=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    embed_url: str = Field(nullable=False, default="")
    blurhash: str = Field(nullable=False, default="")
    language: str = Field(nullable=False, default="")

    statuses: list["Status"] = Relationship(
        back_populates="preview_card", link_model=PreviewCardStatus
    )
