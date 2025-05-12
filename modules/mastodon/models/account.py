
from typing import Annotated, Union
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

from .user import User
from .favourite import Favourite
from config import config

AUTOMATED_ACTOR_TYPES = ['Service', 'Application']

class AccountStats(SQLModel, table=True):
    __tablename__ = 'account_stats'

    account_id: int = Field(primary_key=True, foreign_key='accounts.id')
    statuses_count: int = Field(nullable=False, default=0)
    following_count: int = Field(nullable=False, default=0)
    followers_count: int = Field(nullable=False, default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_status_at: datetime = Field()

    account: "Account" = Relationship(back_populates='stats', sa_relationship_kwargs={"uselist": False})

class Account(SQLModel, table=True):
    __tablename__ = 'accounts'

    id: int | None = Field(primary_key=True)
    username: str = Field(nullable=False)
    domain: str | None = Field()
    created_at: datetime | None = Field()
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    silenced_at: datetime | None = Field()
    suspended_at: datetime | None = Field()
    sensitized_at: datetime | None = Field()
    display_name: str = Field(nullable=False)
    note: str = Field(nullable=False)
    uri: str = Field(nullable=False)
    url: str | None = Field()
    avatar_file_name: str | None = Field()
    header_file_name: str | None = Field()
    discoverable: bool | None = Field(default=False)
    indexable: bool = Field(default=False)
    locked: bool = Field(default=False)
    moved_to_account_id: int | None = Field(foreign_key='accounts.id')
    actor_type: str = Field(default='')

    favourites: list[Favourite] = Relationship(back_populates='account')
    statuses: list["Status"] = Relationship(back_populates='account')
    stats: AccountStats = Relationship(back_populates='account', sa_relationship_kwargs={"uselist": False})
    user: User = Relationship(back_populates='account')

    @property
    def local(self):
        return self.domain is None
    
    @property
    def acct(self):
        if self.domain is None:
            return self.username
        return f"{self.username}@{self.domain}"

    @property
    def pretty_acct(self):
        if self.domain is None:
            return self.username
        # TODO:
        return f"{self.username}@{self.domain}"

    @property
    def header_url(self):
        return config.files.build_file_url(
            self.__tablename__,
            attachment='headers',
            instance_id=self.id,
            file_name=self.header_file_name,
        )

    @property
    def header_static_url(self):
        return self.header_url

    @property
    def avatar_url(self):
        return config.files.build_file_url(
            self.__tablename__,
            attachment='avatars',
            instance_id=self.id,
            file_name=self.avatar_file_name,
        )

    @property
    def avatar_static_url(self):
        return self.avatar_url

    @property
    def bot(self):
        return self.actor_type in AUTOMATED_ACTOR_TYPES

    @property
    def group(self):
        return self.actor_type == 'Group'