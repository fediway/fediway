
from typing import List
from datetime import datetime
from sqlalchemy import Column, ARRAY, Integer, String
from sqlmodel import SQLModel, Field, Relationship
    
class InstanceAccount(SQLModel, table=True):
    __tablename__ = 'instance_accounts'

    account_id: int = Field(primary_key=True, foreign_key="accounts.id")
    domain: str = Field(primary_key=True, foreign_key="known_instances.domain")
    domain_id: str = Field(nullable=False)

class Instance(SQLModel, table=True):
    __tablename__ = 'known_instances'

    domain: str = Field(primary_key=True)
    title: str = Field(default='', nullable=False)
    description: str = Field(default='', nullable=False)
    icon_url: str | None = Field()
    source_url: str | None = Field()
    version: str | None = Field()
    api_version: str = Field(default='', nullable=False)
    api_type: str = Field(default='', nullable=False)
    languages: List[str] = Field(sa_column=Column(ARRAY(String())))
    created_at: datetime | None = Field(default=None, nullable=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    accounts: List["Account"] = Relationship(back_populates="instances", link_model=InstanceAccount)
    instance_accounts: list[InstanceAccount] = Relationship()