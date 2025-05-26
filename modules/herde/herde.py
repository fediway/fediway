import pandas as pd
from arango.graph import Graph

from modules.mastodon.models import (
    Account,
    Favourite,
    Follow,
    Mention,
    Status,
    StatusTag,
    Tag,
)

from .utils import parse_datetime


def default(value, fallback):
    return value if not pd.isna(value) else fallback


class Herde:
    graph: Graph

    def __init__(self, graph: Graph):
        self.graph = graph

        self.accounts = graph.vertex_collection("accounts")
        self.statuses = graph.vertex_collection("statuses")
        self.tags = graph.vertex_collection("tags")

        self.follows = graph.edge_collection("follows")
        self.tagged = graph.edge_collection("tagged")
        self.engaged = graph.edge_collection("engaged")
        self.created = graph.edge_collection("created")
        self.mentioned = graph.edge_collection("mentioned")

    def add_tag(self, tag: Tag):
        self.tags.insert(
            {
                "_key": str(tag.id),
                "name": tag.name,
            },
            overwrite=True,
        )

    def remove_tag(self, tag: Tag):
        self.tags.delete({"_key": str(tag.id)})

    def add_account(self, account: Account):
        if account.id <= 0:
            return

        self.accounts.insert(
            {
                "_key": str(account.id),
                "username": account.username,
                "domain": default(account.domain, ""),
            }
        )

    def add_accounts(self, accounts: list[Account]):
        self.accounts.import_bulk(
            [
                {
                    "_key": str(account.id),
                    "username": account.username,
                    "domain": default(account.domain, ""),
                }
                for account in accounts
                if account.id > 0
            ],
            overwrite=True,
        )

    def remove_account(self, account: Account):
        self.accounts.delete({"_key": tag.id})

    def add_follow(self, follow: Follow):
        self.follows.insert(
            {
                "_from": f"accounts/{follow.account_id}",
                "_to": f"accounts/{follow.target_account_id}",
                "created_at": parse_timestamp(follow.created_at),
            }
        )

    def add_follows(self, follows: list[Follow]):
        self.follows.import_bulk(
            [
                {
                    "_from": f"accounts/{follow.account_id}",
                    "_to": f"accounts/{follow.target_account_id}",
                    "created_at": parse_datetime(follow.created_at),
                }
                for follow in follows
            ],
            overwrite=True,
        )

    def remove_follow(self, follow: Follow):
        self.follows.delete(
            {
                "_from": f"accounts/{follow.account_id}",
                "_to": f"accounts/{follow.target_account_id}",
            }
        )

    def add_favourite(self, favourite: Favourite):
        self.engaged.insert(
            {
                "_from": f"accounts/{favourite.account_id}",
                "_to": f"statuses/{favourite.status_id}",
                "event_time": parse_datetime(favourite.created_at),
                "type": "favourite",
            },
            silent=True,
        )

    def add_favourites(self, favourites: list[Favourite]):
        self.engaged.import_bulk(
            [
                {
                    "_from": f"accounts/{favourite.account_id}",
                    "_to": f"statuses/{favourite.status_id}",
                    "event_time": parse_datetime(favourite.created_at),
                    "type": "favourite",
                }
                for favourite in favourites
            ],
            overwrite=True,
        )

    def add_mentions(self, mentions: list[Mention]):
        self.mentioned.import_bulk(
            [
                {
                    "_from": f"statuses/{mention.status_id}",
                    "_to": f"accounts/{mention.account_id}",
                }
                for mention in mentions
            ],
            overwrite=True,
        )

    def add_status_tags(self, status_tags: list[StatusTag]):
        self.tagged.import_bulk(
            [
                {
                    "_from": f"statuses/{status_tag.status_id}",
                    "_to": f"tags/{status_tag.tag_id}",
                }
                for status_tag in status_tags
            ],
            overwrite=True,
        )

    def remove_favourite(self, favourite: Favourite):
        self.favourited.delete(
            {
                "_from": f"accounts/{favourite.account_id}",
                "_to": f"status/{favourite.status_id}",
            },
            overwrite=True,
        )

    def add_reblog(self, reblog: Status):
        if status.reblog_of_id is None:
            return

        self.reblogged.insert(
            {
                "_from": f"accounts/{status.account_id}",
                "_to": f"status/{status.reblog_of_id}",
                "created_at": parse_datetime(status.created_at),
            },
            overwrite=True,
        )

    def add_status(self, status: Status):
        if not pd.isna(status.reblog_of_id):
            self.engaged.insert(
                {
                    "_from": f"accounts/{status.account_id}",
                    "_to": f"statuses/{status.id}",
                    "event_time": parse_datetime(status.created_at),
                    "type": "reblog",
                }
            )

            return

        self.statuses.insert(
            {
                "_key": str(status.id),
                "language": status.language,
                "created_at": parse_datetime(status.created_at),
            },
            overwrite=True,
            silent=True,
        )

        self.created.insert(
            {
                "_from": f"accounts/{status.account_id}",
                "_to": f"statuses/{status.id}",
            },
            overwrite=True,
            silent=True,
        )

        if not pd.isna(status.in_reply_to_id):
            self.engaged.insert(
                {
                    "_from": f"accounts/{status.account_id}",
                    "_to": f"statuses/{status.in_reply_to_id}",
                    "event_time": parse_datetime(status.created_at),
                    "type": "reblog",
                },
                overwrite=True,
                silent=True,
            )

    def add_statuses(self, statuses: list[Status]):
        reblogs = [status for status in statuses if not pd.isna(status.reblog_of_id)]
        replies = [status for status in statuses if not pd.isna(status.in_reply_to_id)]
        statuses = [status for status in statuses if pd.isna(status.reblog_of_id)]

        if len(statuses) > 0:
            self.statuses.import_bulk(
                [
                    {
                        "_key": str(status.id),
                        "language": default(status.language, ""),
                        "created_at": parse_datetime(status.created_at),
                    }
                    for status in statuses
                ],
                overwrite=True,
            )

            self.created.import_bulk(
                [
                    {
                        "_from": f"accounts/{status.account_id}",
                        "_to": f"statuses/{status.id}",
                    }
                    for status in statuses
                ],
                overwrite=True,
            )

        if len(reblogs) > 0:
            self.engaged.import_bulk(
                [
                    {
                        "_from": f"accounts/{reblog.account_id}",
                        "_to": f"statuses/{reblog.reblog_of_id}",
                        "event_time": parse_datetime(reblog.created_at),
                        "type": "reblog",
                    }
                    for reblog in reblogs
                ],
                overwrite=True,
            )

        if len(replies) > 0:
            self.engaged.import_bulk(
                [
                    {
                        "_from": f"accounts/{reply.account_id}",
                        "_to": f"statuses/{reply.reblog_of_id}",
                        "event_time": parse_datetime(reply.created_at),
                        "type": "reply",
                    }
                    for reply in replies
                ],
                overwrite=True,
            )
