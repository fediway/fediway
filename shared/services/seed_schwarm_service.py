from datetime import datetime, timedelta

import pandas as pd
from dask import dataframe as dd
from dask.base import normalize_token
from loguru import logger
from neo4j import Driver
from sqlalchemy import and_
from sqlmodel import Session as DBSession
from sqlmodel import exists, func, select

import modules.utils as utils
from config import config
from modules.mastodon.models import (
    Favourite,
    Mention,
    Status,
    StatusStats,
    StatusTag,
)
from modules.schwarm import Schwarm


class SeedSchwarmService:
    def __init__(self, db: DBSession, driver: Driver):
        self.db = db
        self.driver = driver
        self.schwarm = Schwarm(self.driver)
        self.max_age = datetime.now() - timedelta(days=config.fediway.feed_max_age_in_days)

    def seed(self):
        with utils.duration("Set up memgraph in {:.3f} seconds"):
            self.schwarm.setup()

        with utils.duration("Seeded statuses in {:.3f} seconds"):
            self.seed_statuses()

        with utils.duration("Seeded reblogs in {:.3f} seconds"):
            self.seed_reblogs()

        with utils.duration("Created favourite seeds in {:.3f} seconds"):
            self.seed_favourites()

        with utils.duration("Created status tag seeds in {:.3f} seconds"):
            self.seed_statuses_tags()

        with utils.duration("Created mention seeds in {:.3f} seconds"):
            self.seed_mentions()

        logger.info("Start computing account ranks...")
        with utils.duration("Computed account ranks in {:.3f} seconds"):
            self.schwarm.compute_account_rank()

        logger.info("Start computing tag ranks...")
        with utils.duration("Computed tag ranks in {:.3f} seconds"):
            self.schwarm.compute_tag_rank()

        logger.info("Start computing communities...")
        with utils.duration("Computed communities in {:.3f} seconds"):
            self.schwarm.compute_communities()

        with utils.duration("Seeded status stats in {:.3f} seconds"):
            self.seed_status_stats()

    def seed_statuses(self, batch_size: int = 100):
        query = (
            select(
                Status.id,
                Status.account_id,
                Status.language,
                Status.created_at,
            )
            .where(Status.created_at > self.max_age)
            .where(Status.reblog_of_id.is_(None))
        )
        total = self.db.scalar(
            select(func.count(Status.id))
            .where(Status.created_at > self.max_age)
            .where(Status.reblog_of_id.is_(None))
        )

        logger.info(f"Inserting {total} statuses.")

        (
            dd.read_sql_query(
                sql=query,
                con=self.db.get_bind().url.render_as_string(hide_password=False),
                index_col="id",
                npartitions=max(1, total // 1_000),
                meta=pd.DataFrame(
                    {
                        "account_id": pd.Series([], dtype="int64"),
                        "language": pd.Series([], dtype="string"),
                        "created_at": pd.Series([], dtype="datetime64[ms]"),
                    }
                ),
            )
            .map_partitions(InsertStatuses(self.db, self.schwarm))
            .compute()
        )

    def seed_reblogs(self, batch_size: int = 100):
        query = (
            select(
                Status.id,
                Status.account_id,
                Status.language,
                Status.created_at,
            )
            .where(Status.created_at > self.max_age)
            .where(~Status.reblog_of_id.is_(None))
        )

        total = self.db.scalar(
            select(func.count(Status.id))
            .where(Status.created_at > self.max_age)
            .where(~Status.reblog_of_id.is_(None))
        )

        if total == 0:
            return

        logger.info(f"Inserting {total} reblogs.")

        (
            dd.read_sql_query(
                sql=query,
                con=self.db.get_bind().url.render_as_string(hide_password=False),
                index_col="id",
                npartitions=max(1, total // 1_000),
                meta=pd.DataFrame(
                    {
                        "account_id": pd.Series([], dtype="int64"),
                        "language": pd.Series([], dtype="string"),
                        "created_at": pd.Series([], dtype="datetime64[ms]"),
                    }
                ),
            )
            .map_partitions(InsertReblogs(self.db, self.schwarm))
            .compute()
        )

    def seed_favourites(self, batch_size: int = 100):
        query = select(Favourite.id, Favourite.account_id, Favourite.status_id).where(
            exists(Status).where(
                and_(
                    Status.id.label("sid") == Favourite.status_id,
                    Status.created_at > self.max_age,
                )
            )
        )

        total = self.db.scalar(
            select(func.count(Favourite.id)).join(
                Status,
                and_(Status.id == Favourite.status_id, Status.created_at > self.max_age),
            )
        )

        if total == 0:
            return

        logger.info(f"Inserting {total} favourites.")

        (
            dd.read_sql_query(
                sql=query,
                con=self.db.get_bind().url.render_as_string(hide_password=False),
                index_col="id",
                npartitions=max(1, total // 1_000),
                meta=pd.DataFrame(
                    {
                        "account_id": pd.Series([], dtype="int64"),
                        "status_id": pd.Series([], dtype="int64"),
                    }
                ),
            )
            .map_partitions(InsertFavourites(self.db, self.schwarm))
            .compute()
        )

    def seed_status_stats(self, batch_size: int = 100):
        query = select(
            StatusStats.status_id,
            StatusStats.replies_count,
            StatusStats.reblogs_count,
            StatusStats.favourites_count,
        ).join(
            Status,
            and_(
                Status.id == StatusStats.status_id,
                Status.created_at > self.max_age,
                Status.reblog_of_id.is_(None),
            ),
        )

        total = self.db.scalar(
            select(func.count(StatusStats.status_id)).join(
                Status,
                and_(
                    Status.id == StatusStats.status_id,
                    Status.created_at > self.max_age,
                    Status.reblog_of_id.is_(None),
                ),
            )
        )

        logger.info(f"Inserting {total} status stats.")

        (
            dd.read_sql_query(
                sql=query,
                con=self.db.get_bind().url.render_as_string(hide_password=False),
                index_col="status_id",
                npartitions=max(1, total // 1_000),
                meta=pd.DataFrame(
                    {
                        "replies_count": pd.Series([], dtype="int64"),
                        "reblogs_count": pd.Series([], dtype="int64"),
                        "favourites_count": pd.Series([], dtype="int64"),
                    }
                ),
            )
            .map_partitions(InsertStatusStats(self.db, self.schwarm))
            .compute()
        )

    def seed_statuses_tags(self, batch_size: int = 100):
        query = select(StatusTag.status_id, StatusTag.tag_id).where(
            exists(Status).where(
                and_(
                    Status.id.label("sid") == StatusTag.status_id,
                    Status.created_at > self.max_age,
                )
            )
        )

        total = self.db.scalar(
            select(func.count(StatusTag.status_id)).where(
                exists(Status).where(
                    and_(
                        Status.id.label("sid") == StatusTag.status_id,
                        Status.created_at > self.max_age,
                    )
                )
            )
        )

        logger.info(f"Inserting {total} status tags.")

        (
            dd.read_sql_query(
                sql=query,
                con=self.db.get_bind().url.render_as_string(hide_password=False),
                index_col="status_id",
                npartitions=max(1, total // 1_000),
                meta=pd.DataFrame(
                    {
                        "tag_id": pd.Series([], dtype="int64"),
                    }
                ),
            )
            .map_partitions(InsertStatusTags(self.db, self.schwarm))
            .compute()
        )

    def seed_mentions(self, batch_size: int = 100):
        query = select(Mention.id, Mention.status_id, Mention.account_id).where(
            exists(Status).where(
                and_(
                    Status.id.label("sid") == Mention.status_id,
                    Status.created_at > self.max_age,
                )
            )
        )

        total = self.db.scalar(
            select(func.count(Mention.id)).where(
                exists(Status).where(
                    and_(
                        Status.id.label("sid") == Mention.status_id,
                        Status.created_at > self.max_age,
                    )
                )
            )
        )

        logger.info(f"Inserting {total} mentions.")

        (
            dd.read_sql_query(
                sql=query,
                con=self.db.get_bind().url.render_as_string(hide_password=False),
                index_col="id",
                npartitions=max(1, total // 1_000),
                meta=pd.DataFrame(
                    {
                        "status_id": pd.Series([], dtype="int64"),
                        "account_id": pd.Series([], dtype="int64"),
                    }
                ),
            )
            .map_partitions(InsertMentions(self.db, self.schwarm))
            .compute()
        )


class InsertBatch:
    def __init__(self, db, schwarm):
        self.db = db
        self.schwarm = schwarm

    def __dask_tokenize__(self):
        return normalize_token(type(self))


class InsertStatuses(InsertBatch):
    def __call__(self, rows) -> None:
        if len(rows) == 0:
            return

        statuses = [Status(id=id, **data) for id, data in rows.iterrows()]

        if statuses[0].id in (0, 1):
            return

        self.schwarm.add_statuses(statuses)


class InsertStatusStats(InsertBatch):
    def __call__(self, rows) -> None:
        if len(rows) == 0:
            return

        stats = [StatusStats(status_id=status_id, **data) for status_id, data in rows.iterrows()]

        if stats[0].status_id in (0, 1):
            return

        self.schwarm.add_status_stats_batch(stats)


class InsertStatusTags(InsertBatch):
    def __call__(self, rows) -> None:
        if len(rows) == 0:
            return

        status_tags = [
            StatusTag(status_id=status_id, **data) for status_id, data in rows.iterrows()
        ]

        if status_tags[0].status_id == 1:
            return

        self.schwarm.add_status_tags(status_tags)


class InsertReblogs(InsertBatch):
    def __call__(self, rows) -> None:
        if len(rows) == 0:
            return

        reblogs = [Status(id=id, **data) for id, data in rows.iterrows()]

        if reblogs[0].id in (0, 1):
            return

        self.schwarm.add_reblogs(reblogs)


class InsertFavourites(InsertBatch):
    def __call__(self, rows) -> None:
        if len(rows) == 0:
            return

        favourites = [Favourite(id=id, **data) for id, data in rows.iterrows()]

        if favourites[0].account_id in (0, 1):
            return

        self.schwarm.add_favourites(favourites)


class InsertMentions(InsertBatch):
    def __call__(self, rows) -> None:
        if len(rows) == 0:
            return

        mentions = [Mention(id=id, **data) for id, data in rows.iterrows()]

        if mentions[0].account_id in (0, 1):
            return

        self.schwarm.add_mentions(mentions)
