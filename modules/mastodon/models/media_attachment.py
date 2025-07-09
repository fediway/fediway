from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

from config import config


class MediaAttachment(SQLModel, table=True):
    __tablename__ = "media_attachments"

    id: int = Field(primary_key=True)
    type: int = Field(nullable=False)
    status_id: int = Field(foreign_key="statuses.id")
    account_id: int = Field(foreign_key="accounts.id")
    description: str = Field()
    remote_url: str | None = Field()
    blurhash: str | None = Field()

    file_file_name: str | None = Field()
    file_meta: dict = Field(sa_column=Column(JSON()))

    thumbnail_file_name: str | None = Field()

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    status: "Status" = Relationship(back_populates="media_attachments")

    @property
    def file_url(self):
        return config.files.build_file_url(
            self.__tablename__,
            attachment="files",
            instance_id=self.id,
            file_name=self.file_file_name,
            cache=self.remote_url is not None and self.remote_url != "",
        )

    @property
    def thumbnail_url(self):
        if self.thumbnail_file_name is None:
            return

        return config.files.build_file_url(
            self.__tablename__,
            attachment="files",
            instance_id=self.id,
            file_name=self.thumbnail_file_name,
            style="small",
        )

    @property
    def preview_url(self):
        return self.thumbnail_url or self.file_url
