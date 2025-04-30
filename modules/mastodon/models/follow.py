
from datetime import datetime
from sqlmodel import SQLModel, Field

class Follow(SQLModel, table=True):
    __tablename__ = 'follows'

    id: int | None = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    account_id: int = Field(nullable=False)
    target_account_id: int = Field(nullable=False)