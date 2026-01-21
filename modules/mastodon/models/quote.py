from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from config import config


class Quote(SQLModel, table=True):
    __tablename__ = "quotes"

    account_id: str = Field(nullable=False, primary_key=True, foreign_key="accounts.id")
    status_id: str = Field(nullable=True, primary_key=True, foreign_key="statuses.id")
    quoted_status_id: str = Field(
        nullable=True, primary_key=True, foreign_key="statuses.id"
    )
    quoted_account_id: str = Field(
        nullable=True, primary_key=True, foreign_key="accounts.id"
    )

    state: int = Field(nullable=False)

    status: Optional["Status"] = Relationship(
        back_populates="quote",
        sa_relationship_kwargs={
            "foreign_keys": "Quote.status_id",
        },
    )
    quoted_status: "Status" = Relationship(
        back_populates="quotes",
        sa_relationship_kwargs={
            "foreign_keys": "Quote.quoted_status_id",
        },
    )

    account: "Account" = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "Quote.account_id",
        },
    )
