from datetime import datetime

from sqlmodel import Field, SQLModel


class Feed(SQLModel, table=True):
    __tablename__ = "feeds"

    id: int = Field(primary_key=True)
    session_id: str = Field(nullable=False)
    user_agent: str = Field(nullable=False)
    ip: str = Field(nullable=False)
    name: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)