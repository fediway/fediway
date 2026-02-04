from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from config import config

if TYPE_CHECKING:
    from .status import Status


class PreviewCardStatus(SQLModel, table=True):
    __tablename__ = "preview_cards_statuses"

    preview_card_id: int = Field(nullable=False, primary_key=True, foreign_key="preview_cards.id")
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
    image_file_name: str | None = Field()
    width: int = Field(nullable=False, default=0)
    height: int = Field(nullable=False, default=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    embed_url: str = Field(nullable=False, default="")
    blurhash: str = Field(nullable=False, default="")
    language: str = Field(nullable=False, default="")

    statuses: list["Status"] = Relationship(
        back_populates="preview_card", link_model=PreviewCardStatus
    )

    @property
    def image_url(self):
        return config.files.build_file_url(
            self.__tablename__,
            attachment="images",
            instance_id=self.id,
            file_name=self.image_file_name,
        )
