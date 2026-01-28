import pandas as pd
from arango.graph import Graph
from dask import dataframe as dd
from dask.base import normalize_token
from dask.diagnostics import ProgressBar
from loguru import logger
from sqlmodel import Session as DBSession
from sqlmodel import select

import modules.utils as utils
from modules.herde import Herde
from modules.mastodon.models import (
    Account,
    Favourite,
    Follow,
    Mention,
    Status,
    StatusTag,
    Tag,
)


class SeedHerdeService:
    def __init__(self, db: DBSession, graph: Graph):
        self.db = db
        self.herde = Herde(graph)

    def seed(self):
        with utils.duration("Seeded accounts in {:.3f} seconds"):
            self.seed_table(Account)

        with utils.duration("Seeded tags in {:.3f} seconds"):
            self.seed_table(Tag)

        with utils.duration("Seeded follows in {:.3f} seconds"):
            self.seed_table(Follow)

        with utils.duration("Seeded statuses in {:.3f} seconds"):
            self.seed_statuses()

        with utils.duration("Seeded favourites in {:.3f} seconds"):
            self.seed_table(Favourite)

        # with utils.duration("Seeded status stats in {:.3f} seconds"):
        #     self.seed_table(StatusStats, 'add_statuses_stats_batch')

        with utils.duration("Created status tag seeds in {:.3f} seconds"):
            self.seed_statuses_tags()

        with utils.duration("Created mentions seeds in {:.3f} seconds"):
            self.seed_table(Mention)

        exit()

        logger.info("Start computing account ranks...")
        with utils.duration("Computed account ranks in {:.3f} seconds"):
            self.schwarm.compute_account_rank()

        logger.info("Start computing tag ranks...")
        with utils.duration("Computed tag ranks in {:.3f} seconds"):
            self.schwarm.compute_tag_rank()

    def seed_table(self, model_cls, herde_fn=None):
        map_fn = InsertRows(self.db, self.herde, model_cls, herde_fn)

        ddf = dd.read_sql_table(
            model_cls.__tablename__,
            con=self.db.get_bind().url.render_as_string(hide_password=False),
            index_col="id",
        ).map_partitions(map_fn)

        with ProgressBar():
            ddf.compute()

    def seed_statuses(self, batch_size: int = 100):
        query = (
            select(
                Status.id,
                Status.account_id,
                Status.language,
                Status.created_at,
                Status.in_reply_to_id,
                Status.reblog_of_id,
            )
            # .where(Status.created_at > self.max_age)
        )

        ddf = dd.read_sql_query(
            sql=query,
            con=self.db.get_bind().url.render_as_string(hide_password=False),
            index_col="id",
            bytes_per_chunk="64 MiB",
        ).map_partitions(
            InsertRows(
                self.db,
                self.herde,
                Status,
            )
        )

        with ProgressBar():
            ddf.compute()

    def seed_statuses_tags(self, batch_size: int = 100):
        query = select(StatusTag.status_id, StatusTag.tag_id)

        ddf = dd.read_sql_query(
            sql=query,
            con=self.db.get_bind().url.render_as_string(hide_password=False),
            index_col="status_id",
            bytes_per_chunk="64 MiB",
            meta=pd.DataFrame(
                {
                    "tag_id": pd.Series([], dtype="int64"),
                }
            ),
        ).map_partitions(InsertStatusTags(self.db, self.herde))

        with ProgressBar():
            ddf.compute()


class InsertBatch:
    def __init__(self, db: DBSession, herde: Herde):
        self.db = db
        self.herde = herde

    def __dask_tokenize__(self):
        return normalize_token(type(self))


class InsertRows(InsertBatch):
    def __init__(self, db: DBSession, herde: Herde, model_cls, herde_fn: str | None = None):
        self.db = db
        self.herde = herde
        self.model_cls = model_cls
        self.herde_fn = herde_fn or f"add_{model_cls.__tablename__}"

    def __call__(self, rows: pd.DataFrame) -> None:
        if len(rows) == 0:
            return

        models = [self.model_cls(id=id, **data) for id, data in rows.iterrows()]

        id_column = "id"
        if self.model_cls in [Favourite, Mention, Follow]:
            id_column = "account_id"

        if getattr(models[0], id_column) in (0, 1):
            return

        getattr(self.herde, self.herde_fn)(models)


class InsertStatusTags(InsertBatch):
    def __call__(self, rows) -> None:
        if len(rows) == 0:
            return

        status_tags = [
            StatusTag(status_id=status_id, **data) for status_id, data in rows.iterrows()
        ]

        if status_tags[0].status_id == 1:
            return

        self.herde.add_status_tags(status_tags)
