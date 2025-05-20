from feast import FeatureStore
from dask import dataframe as dd
from dask.diagnostics import ProgressBar
from dask.base import normalize_token
from dask.utils import parse_bytes

from sklearn.model_selection import train_test_split
import pandas as pd

import time
from sqlmodel import Session, select
from sqlalchemy import (
    text,
    insert,
)
from datetime import datetime, date

import modules.utils as utils
from modules.fediway.models.risingwave import AccountStatusLabel
from modules.features import get_historical_features_ddf, create_entities_table
from .features import get_feature_views


class InsertPositives:
    def __init__(self, db, table):
        self.db = db
        self.table = table

    def __call__(self, labels):
        values = [
            {
                "account_id": label.account_id,
                "status_id": label.status_id,
                "author_id": author_id,
                "time": label.status_created_at,
            }
            for author_id, label in labels.iterrows()
        ]

        if len(values) > 0 and values[0]["account_id"] != 1:
            self.db.exec(insert(self.table).values(values))
            self.db.commit()

    def __dask_tokenize__(self):
        return normalize_token(type(self)), self.table.name


class NegativeSampler:
    def __init__(self, db, table, start_date, end_date):
        self.db = db
        self.table = table
        self.start_date = start_date
        self.end_date = end_date

    def _get_date_clause(self):
        query = f"s.created_at < '{self.end_date.strftime('%Y-%m-%d')}'"
        if self.start_date is not None:
            query += f" AND s.created_at >= '{self.end_date.strftime('%Y-%m-%d')}'"
        return query

    def _insert_batch(self, batch):
        values = [
            {
                "account_id": row.account_id,
                "status_id": status_id,
                "author_id": row.author_id,
                "time": row.time,
            }
            for status_id, row in batch.iterrows()
            if isinstance(row.time, datetime)
        ]

        if len(values) > 0 and values[0]["account_id"] != 1:
            self.db.exec(insert(self.table).values(values))
            self.db.commit()


class EngagedAuthorNegativeSampler(NegativeSampler):
    def __call__(self):
        query = select(
            text(f"""
            s.id,
            n.account_id,
            n.status_id,
            s.account_id AS author_id,
            s.created_at AS time
        FROM statuses s
        JOIN (
            SELECT 
                d.account_id,
                s.id AS status_id
            FROM {self.table.name} d
            CROSS JOIN LATERAL (
                SELECT s.id
                FROM statuses s
                WHERE s.id < d.status_id
                  AND s.account_id = d.author_id
                  AND {self._get_date_clause()}
                  AND NOT EXISTS (
                    SELECT 1
                    FROM {self.table.name} d2
                    WHERE d2.status_id = s.id
                      AND d2.account_id = d.account_id
                )
                ORDER BY s.id DESC
                LIMIT 1
            ) s
        ) n ON s.id = n.status_id AND {self._get_date_clause()}
        """)
        )

        min_id = self.db.scalar(
            text(f"SELECT MIN(s.id) FROM statuses s WHERE {self._get_date_clause()}")
        )
        max_id = self.db.scalar(
            text(f"SELECT MAX(s.id) FROM statuses s WHERE {self._get_date_clause()}")
        )
        count_approx = self.db.scalar(
            text(f"SELECT COUNT(d.account_id) FROM {self.table.name} d")
        )
        bytes_per_row = 32
        bytes_per_chunk = "64 MiB"
        npartitions = (
            int(round(count_approx * bytes_per_row / parse_bytes(bytes_per_chunk))) or 1
        )

        ddf = utils.read_sql_join_query(
            sql=query,
            con=self.db.get_bind().url.render_as_string(hide_password=False),
            bytes_per_chunk="64 MiB",
            index_col="id",
            limits=(min_id, max_id),
            npartitions=npartitions,
            head_rows=0,
            meta=pd.DataFrame(
                {
                    "account_id": pd.Series([], dtype="int64"),
                    "status_id": pd.Series([], dtype="int64"),
                    "author_id": pd.Series([], dtype="int64"),
                    "time": pd.Series([], dtype="datetime64[s]"),
                }
            ),
        )

        with ProgressBar():
            ddf.map_partitions(self._insert_batch).compute()

    def __dask_tokenize__(self):
        return normalize_token(type(self)), self.table.name


class FollowingNegativeSampler(NegativeSampler):
    def __call__(self):
        query = select(
            text(f""" 
            s.id,
            n.account_id,
            n.status_id,
            s.account_id AS author_id,
            s.created_at AS time
        FROM statuses s
        JOIN (
            SELECT 
                d.account_id,
                s.id AS status_id
            FROM {self.table.name} d
            CROSS JOIN LATERAL (
                SELECT s.id
                FROM statuses s
                JOIN follows f
                  ON f.account_id = d.account_id
                 AND f.target_account_id = s.account_id
                WHERE s.id < d.status_id
                  AND {self._get_date_clause()}
                  AND NOT EXISTS (
                    SELECT 1
                    FROM {self.table.name} d2
                    WHERE d2.status_id = s.id
                      AND d2.account_id = d.account_id
                )
                ORDER BY s.id DESC
                LIMIT 1
            ) s
        ) n ON s.id = n.status_id AND {self._get_date_clause()}
        """)
        )

        min_id = self.db.scalar(
            text(f"SELECT MIN(s.id) FROM statuses s WHERE {self._get_date_clause()}")
        )
        max_id = self.db.scalar(
            text(f"SELECT MAX(s.id) FROM statuses s WHERE {self._get_date_clause()}")
        )
        count_approx = self.db.scalar(
            text(f"SELECT COUNT(d.account_id) FROM {self.table.name} d")
        )
        bytes_per_row = 32
        bytes_per_chunk = "64 MiB"
        npartitions = (
            int(round(count_approx * bytes_per_row / parse_bytes(bytes_per_chunk))) or 1
        )

        ddf = utils.read_sql_join_query(
            sql=query,
            con=self.db.get_bind().url.render_as_string(hide_password=False),
            bytes_per_chunk="64 MiB",
            index_col="id",
            limits=(min_id, max_id),
            npartitions=npartitions,
            head_rows=0,
            meta=pd.DataFrame(
                {
                    "account_id": pd.Series([], dtype="int64"),
                    "status_id": pd.Series([], dtype="int64"),
                    "author_id": pd.Series([], dtype="int64"),
                    "time": pd.Series([], dtype="datetime64[s]"),
                }
            ),
        )

        with ProgressBar():
            ddf.map_partitions(self._insert_batch).compute()

    def __dask_tokenize__(self):
        return normalize_token(type(self)), self.table.name


class RandomNegativeSampler(NegativeSampler):
    def __call__(self):
        query = select(
            text(f""" 
            s.id,
            n.account_id,
            n.status_id,
            s.account_id AS author_id,
            s.created_at AS time
        FROM statuses s
        JOIN (
            SELECT 
                d.account_id,
                s.id AS status_id
            FROM {self.table.name} d
            CROSS JOIN LATERAL (
                SELECT s.id
                FROM statuses s
                WHERE s.id < d.status_id
                  AND {self._get_date_clause()}
                  AND NOT EXISTS (
                    SELECT 1
                    FROM {self.table.name} d2
                    WHERE d2.status_id = s.id
                      AND d2.account_id = d.account_id
                )
                ORDER BY s.id DESC
                LIMIT 1
            ) s
        ) n ON s.id = n.status_id AND {self._get_date_clause()}
        """)
        )

        min_id = self.db.scalar(
            text(f"SELECT MIN(s.id) FROM statuses s WHERE {self._get_date_clause()}")
        )
        max_id = self.db.scalar(
            text(f"SELECT MAX(s.id) FROM statuses s WHERE {self._get_date_clause()}")
        )
        count_approx = self.db.scalar(
            text(f"SELECT COUNT(d.account_id) FROM {self.table.name} d")
        )
        bytes_per_row = 32
        bytes_per_chunk = "64 MiB"
        npartitions = (
            int(round(count_approx * bytes_per_row / parse_bytes(bytes_per_chunk))) or 1
        )

        ddf = utils.read_sql_join_query(
            sql=query,
            con=self.db.get_bind().url.render_as_string(hide_password=False),
            index_col="account_id",
            bytes_per_chunk="64 MiB",
            limits=(min_id, max_id),
            npartitions=npartitions,
            head_rows=0,
            meta=pd.DataFrame(
                {
                    "status_id": pd.Series([], dtype="int64"),
                    "author_id": pd.Series([], dtype="int64"),
                    "time": pd.Series([], dtype="datetime64[s]"),
                }
            ),
        )

        with ProgressBar():
            ddf.map_partitions(self._insert_batch).compute()

    def __dask_tokenize__(self):
        return normalize_token(type(self)), self.table.name


def _sample_positives(db, table, start_date, end_date):
    query = select(AccountStatusLabel).where(
        AccountStatusLabel.status_created_at < end_date
    )
    if start_date is not None:
        query = query.where(AccountStatusLabel.status_created_at >= start_date)

    ddf = dd.read_sql_query(
        sql=query,
        con=db.get_bind().url.render_as_string(hide_password=False),
        index_col="author_id",
        bytes_per_chunk="64 MiB",
        meta=pd.DataFrame(
            {
                "account_id": pd.Series([], dtype="int64"),
                "status_id": pd.Series([], dtype="int64"),
                "status_created_at": pd.Series([], dtype="datetime64[s]"),
                "is_favourited": pd.Series([], dtype="bool"),
                "is_reblogged": pd.Series([], dtype="bool"),
                "is_replied": pd.Series([], dtype="bool"),
                "is_reply_engaged_by_author": pd.Series([], dtype="bool"),
                "is_favourited_at": pd.Series([], dtype="datetime64[s]"),
                "is_reblogged_at": pd.Series([], dtype="datetime64[s]"),
                "is_replied_at": pd.Series([], dtype="datetime64[s]"),
                "is_reply_engaged_by_author_at": pd.Series([], dtype="datetime64[s]"),
            }
        ),
    )

    with ProgressBar():
        ddf.map_partitions(InsertPositives(db, table)).compute()
    db.commit()


def _sample_negatives(db, table, start_date, end_date):
    # sample negatives from statuses of engaged author
    negative_samplers = [
        EngagedAuthorNegativeSampler(db, table, start_date, end_date),
        FollowingNegativeSampler(db, table, start_date, end_date),
        # RandomNegativeSampler(db, table, start_date, end_date),
    ]

    for sampler in negative_samplers:
        print(f"Start sampling {sampler}")
        with utils.duration("Sampled negatives in {:.3f} seconds."):
            sampler()


def create_dataset(
    path: str,
    fs: FeatureStore,
    db: Session,
    name: str,
    start_date: date | None = None,
    end_date: date = datetime.now().date(),
    test_size: float = 0.2,
    storage_options={},
):
    table = create_entities_table(name.replace("-", "_"), db)
    feature_views = get_feature_views(fs)

    with utils.duration("Sampled positives in {:.3f} seconds."):
        _sample_positives(db, table, start_date, end_date)

    time.sleep(1.0)

    _sample_negatives(db, table, start_date, end_date)

    with ProgressBar():
        ddf = get_historical_features_ddf(
            entity_table=table.name, feature_views=feature_views, db=db
        )
        ddf.to_parquet(
            f"{path}/data/", write_index=False, storage_options=storage_options
        )

    db.exec(text(f"DROP TABLE IF EXISTS {table.name};"))
    db.commit()

    unique_account_ids = (
        dd.read_parquet(
            f"{path}/data/", columns=["account_id"], storage_options=storage_options
        )
        .drop_duplicates()
        .compute()
    )

    train_accounts, test_accounts = train_test_split(
        unique_account_ids, test_size=test_size, random_state=42
    )

    train_accounts_dd = dd.from_pandas(
        train_accounts, npartitions=(len(train_accounts) // 10_000) + 1
    )
    test_accounts_dd = dd.from_pandas(
        test_accounts, npartitions=(len(test_accounts) // 10_000) + 1
    )

    df_full = dd.read_parquet(
        f"{path}/data/", storage_options=storage_options, blocksize="64MB"
    )

    train_ddf = df_full.merge(train_accounts_dd, on="account_id", how="inner")
    test_ddf = df_full.merge(test_accounts_dd, on="account_id", how="inner")

    train_ddf.to_parquet(
        f"{path}/train/", write_index=False, storage_options=storage_options
    )
    test_ddf.to_parquet(
        f"{path}/test/", write_index=False, storage_options=storage_options
    )
