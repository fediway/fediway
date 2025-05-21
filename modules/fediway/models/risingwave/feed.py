from datetime import datetime

from sqlmodel import Field, SQLModel


class Feed(SQLModel, table=True):
    __tablename__ = "feeds"

    id: str = Field(primary_key=True)
    user_agent: str = Field(nullable=False)
    ip: str = Field(nullable=False)
    name: str = Field(nullable=False)
    entity: str = Field(nullable=False)
    account_id: int = Field(nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
