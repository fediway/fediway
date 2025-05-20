from sqlmodel import SQLModel, Field
from datetime import datetime


class AccountStatusLabel(SQLModel, table=True):
    __tablename__ = "account_status_labels"

    account_id: int = Field(primary_key=True)
    status_id: int = Field(primary_key=True)
    author_id: int = Field()
    status_created_at: datetime = Field()

    is_favourited: bool = Field()
    is_reblogged: bool = Field()
    is_replied: bool = Field()
    is_reply_engaged_by_author: bool = Field()

    is_favourited_at: datetime | None = Field()
    is_reblogged_at: datetime | None = Field()
    is_replied_at: datetime | None = Field()
    is_reply_engaged_by_author_at: datetime | None = Field()
