from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .account import Account


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int = Field(primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")

    account: "Account" = Relationship(back_populates="user")
