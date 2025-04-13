

from datetime import datetime
from sqlmodel import Session, func, select, exists, case, text
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy import and_

from app.modules.models import Status, StatusTag, Account, Favourite

from .base import Feature
from .utils import is_joined

class ARepliedB(Feature):
    __featname__ = 'a_replied_b'

    def query(q, a_label, b_label):
        StatusAlias = aliased(Status)

        q = q.add_columns(
            exists(StatusAlias.id)
            .where(StatusAlias.account_id == a_label)
            .where(StatusAlias.in_reply_to_account_id == b_label)
            .label('a_replied_b')
        )

        return q

    def get(a_replied_b, **kwargs):
        return int(a_replied_b)

class BRepliedA(Feature):
    __featname__ = 'b_replied_a'

    def query(q, a_label, b_label):
        StatusAlias = aliased(Status)

        q = q.add_columns(
            exists(StatusAlias.id)
            .where(StatusAlias.account_id == b_label)
            .where(StatusAlias.in_reply_to_account_id == a_label)
            .label('b_replied_a')
        )

        return q

    def get(b_replied_a, **kwargs):
        return int(b_replied_a)

class NumFavouritesA2B(Feature):
    __featname__ = 'num_favourites_a2b'

    def query(q, a_label, b_label):
        FavouriteAlias = aliased(Favourite)
        StatusAlias = aliased(Status)

        q = (
            q.add_columns(
                func.count(FavouriteAlias.id)
                .filter(
                    exists(StatusAlias.id)
                    .where(StatusAlias.id == FavouriteAlias.status_id)
                    .where(StatusAlias.account_id == b_label)
                )
                .label('num_favourites_a2b')
            )
            .outerjoin(FavouriteAlias, and_(
                FavouriteAlias.account_id == a_label,
                FavouriteAlias.status_id == Status.id
            ))
        )

        return q

    def get(num_favourites_a2b, **kwargs):
        return int(num_favourites_a2b)

class NumFavouritesB2A(Feature):
    __featname__ = 'num_favourites_b2a'

    def query(q, a_label, b_label):
        FavouriteAlias = aliased(Favourite)
        StatusAlias = aliased(Status)

        q = (
            q.add_columns(
                func.count(FavouriteAlias.id)
                .filter(
                    exists(StatusAlias.id)
                    .where(StatusAlias.id == FavouriteAlias.id)
                    .where(StatusAlias.account_id == a_label)
                )
                .label('num_favourites_b2a')
            )
            .outerjoin(FavouriteAlias, FavouriteAlias.account_id == b_label)
        )

        return q

    def get(num_favourites_a2b, **kwargs):
        return int(num_favourites_a2b)