
from typing import List
from datetime import datetime
from sqlalchemy import Column, ARRAY, Integer, BigInteger, String
from sqlmodel import Field, Relationship

from .base import ReadOnlyModel

class Favourite(ReadOnlyModel, table=True):
    __tablename__ = 'favourites'

    id: int = Field(primary_key=True)
    created_at: datetime = Field(nullable=False)
    updated_at: datetime = Field(nullable=False)
    account_id: str = Field(nullable=False, foreign_key="accounts.id")
    status_id: str = Field(nullable=False, foreign_key="statuses.id")

    account: "Account" = Relationship(back_populates="favourites")
    status: "Status" = Relationship(back_populates="favourites")