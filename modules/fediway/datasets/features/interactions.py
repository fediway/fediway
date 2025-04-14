

from datetime import datetime
from sqlmodel import Session, func, select, exists, case, text
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy import and_

from app.modules.models import Status, StatusTag, Account, Favourite, Mention, Follow

from .base import Feature
from .utils import is_joined

class InteractionFeature(Feature):
    @property
    def label(self):
        return f"{self.a_label}.{self.__featname__}.{self.b_label}"

    def __init__(self, a_label, b_label):
        self.a_label = a_label
        self.b_label = b_label

    def get(self, **kwargs) -> int:
        return int(kwargs.get(self.label))

class HasReplied(InteractionFeature):
    __featname__ = 'has_replied'

    def query(self, q):
        StatusAlias = aliased(Status)

        q = (
            q.add_columns(
                func.count(StatusAlias.id).label(self.label)
            )
            .outerjoin(StatusAlias, and_(
                StatusAlias.account_id == self.a_label,
                StatusAlias.in_reply_to_account_id == self.b_label
            ))
        )

        return q

class NumFavourites(InteractionFeature):
    __featname__ = 'num_favourites'

    def query(self, q):
        StatusAlias = aliased(Status)
        FavouriteAlias = aliased(Favourite)

        q = q.add_columns(
            func.count(StatusAlias.id)
            .filter(
                exists()
                .where(FavouriteAlias.status_id == StatusAlias.id)
                .where(FavouriteAlias.account_id == self.a_label)
            )
            .label(self.label)
        ).outerjoin(StatusAlias, StatusAlias.account_id == self.b_label)

        return q

# class NumReblogs(InteractionFeature):
#     __featname__ = 'num_reblogs'

#     def query(self, q):
#         StatusAlias = aliased(Status)
#         FavouriteAlias = aliased(Favourite)

#         q = q.add_columns(
#             func.count(StatusAlias.id)
#             .filter(
#                 exists()
#                 .where(FavouriteAlias.status_id == StatusAlias.id)
#                 .where(FavouriteAlias.account_id == self.a_label)
#             )
#             .label(self.label)
#         ).outerjoin(StatusAlias, StatusAlias.account_id == self.b_label)

#         return q

class NumMentions(InteractionFeature):
    __featname__ = 'num_mentions'

    def query(self, q):
        MentionAlias = aliased(Mention)
        # Statu = aliased(Favourite)

        q = q.add_columns(
            func.count(MentionAlias.id).label(self.label)
        ).outerjoin(MentionAlias, and_(
            MentionAlias.account_id == self.b_label,
            MentionAlias.status_id == Status.id,
        ))

        return q

class IsFollowing(InteractionFeature):
    __featname__ = 'is_following'

    def query(self, q):
        FollowAlias = aliased(Follow)
        # Statu = aliased(Favourite)

        q = q.add_columns(
            func.max(FollowAlias.id).label(self.label)
        ).outerjoin(FollowAlias, and_(
            FollowAlias.account_id == self.a_label,
            FollowAlias.target_account_id == self.b_label,
        ))

        return q

    def get(self, **kwargs) -> int:
        return int(kwargs.get(self.label) is not None)