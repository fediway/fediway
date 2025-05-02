
from feast import FeatureStore
from dask import dataframe as dd
from dask import array as da
from dask.distributed import Client, as_completed
from dask.diagnostics import ProgressBar
from dask.base import normalize_token
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import pandas as pd
import numpy as np

import time
import random
from tqdm import tqdm
from sqlmodel import Session, func, select, exists
from sqlmodel.sql._expression_select_cls import Select
from sqlalchemy.orm import selectinload, joinedload, aliased
from sqlalchemy.schema import CreateTable
from sqlalchemy import label, and_, text, MetaData, Table, DateTime, Column, Integer, BigInteger, String, Float, insert
from datetime import datetime, timedelta, date
from tqdm import tqdm

import modules.utils as utils
from modules.fediway.models.risingwave import AccountStatusLabel
from modules.features import get_historical_features, create_entities_table
from .features import get_feature_views

class InsertPositives:
    def __init__(self, db, table):
        self.db = db
        self.table = table

    def __call__(self, labels):
        values = [{
            'account_id': label.account_id,
            'status_id': label.status_id,
            'author_id': author_id,
            'time': label.status_created_at,
        } for author_id, label in labels.iterrows()]
        
        if len(values) > 0 and values[0]['account_id'] != 1:
            self.db.exec(insert(self.table).values(values))

    def __dask_tokenize__(self):
        return normalize_token(type(self)), self.table.name

class NegativeSampler():
    def __init__(self, db, table):
        self.db = db
        self.table = table

    def _insert_batch(self, batch):
        values = [{
            'account_id': row.account_id,
            'status_id': status_id,
            'author_id': row.author_id,
            'time': row.time,
        } for status_id, row in batch.iterrows()]

        if len(values) > 0 and values[0]['account_id'] != 1:
            self.db.exec(insert(self.table).values(values))

class EngagedAuthorNegativeSampler(NegativeSampler):
    def __call__(self):
        query = select(text(f""" 
            n.account_id,
            n.status_id,
            s.account_id AS author_id,
            s.created_at AS time
        FROM statuses s
        JOIN (
            SELECT 
                ds.account_id,
                MAX(n.id) AS status_id
            FROM {self.table.name} ds
            JOIN statuses n
            ON n.id != ds.status_id 
            AND n.account_id = ds.author_id 
            AND n.id < ds.status_id
            AND n.reblog_of_id IS NULL
            GROUP BY ds.account_id, ds.status_id
        ) n ON s.id = n.status_id
        """))

        ddf = utils.read_sql_join_query(
            sql=query,
            con=self.db.get_bind().url.render_as_string(hide_password=False),
            bytes_per_chunk="64 MiB",
            index_col="status_id",
            meta=pd.DataFrame({
                "account_id": pd.Series([], dtype="int64"),
                "author_id": pd.Series([], dtype="int64"),
                "time": pd.Series([], dtype="datetime64[s]"),
            })
        )

        with ProgressBar():
            ddf.map_partitions(self._insert_batch).compute()
    
    def __dask_tokenize__(self):
        return normalize_token(type(self)), self.table.name

class FollowingNegativeSampler(NegativeSampler):
    def __call__(self):
        query = select(text(f""" 
            n.account_id,
            n.status_id,
            s.account_id AS author_id,
            s.created_at AS time
        FROM statuses s
        JOIN (
            SELECT 
                ds.account_id,
                MAX(n.id) AS status_id
            FROM {self.table.name} ds
            JOIN follows f ON f.account_id = ds.account_id
            JOIN statuses n 
            ON n.id != ds.status_id 
            AND n.account_id = f.target_account_id  
            AND n.id < ds.status_id
            AND n.reblog_of_id IS NULL
            GROUP BY ds.account_id, ds.status_id
        ) n ON s.id = n.status_id
        """))

        ddf = utils.read_sql_join_query(
            sql=query,
            con=self.db.get_bind().url.render_as_string(hide_password=False),
            bytes_per_chunk="64 MiB",
            index_col="status_id",
            meta=pd.DataFrame({
                "account_id": pd.Series([], dtype="int64"),
                "author_id": pd.Series([], dtype="int64"),
                "time": pd.Series([], dtype="datetime64[s]"),
            })
        )

        with ProgressBar():
            ddf.map_partitions(self._insert_batch).compute()
    
    def __dask_tokenize__(self):
        return normalize_token(type(self)), self.table.name

class RandomNegativeSampler(NegativeSampler):
    def __call__(self):
        query = select(text(f""" 
            n.account_id,
            n.status_id,
            s.account_id AS author_id,
            s.created_at AS time
        FROM statuses s
        JOIN (
            SELECT 
                ds.account_id,
                MAX(n.id) AS status_id
            FROM {self.table.name} ds
            JOIN (
                SELECT *
                FROM statuses s
                JOIN {self.table.name} ds
                ON ds.status_id = s.id
                LIMIT 1
            ) n 
            ON n.id != ds.status_id
            AND n.id < ds.status_id
            AND n.reblog_of_id IS NULL
            GROUP BY ds.account_id, ds.status_id
        ) n ON s.id = n.status_id
        """))

        ddf = utils.read_sql_join_query(
            sql=query,
            con=self.db.get_bind().url.render_as_string(hide_password=False),
            index_col="status_id",
            bytes_per_chunk="64 MiB",
            meta=pd.DataFrame({
                "account_id": pd.Series([], dtype="int64"),
                "author_id": pd.Series([], dtype="int64"),
                "time": pd.Series([], dtype="datetime64[s]"),
            })
        )

        with ProgressBar():
            ddf.map_partitions(self._insert_batch).compute()
    
    def __dask_tokenize__(self):
        return normalize_token(type(self)), self.table.name
    
class KirbyDataset():
    @classmethod
    def extract(cls, fs: FeatureStore, db: Session, name: str, start_date: date | None = None, end_date: date = datetime.now().date()):
        total_query = select(func.count(text("*"))).where(AccountStatusLabel.status_created_at < end_date)
        query = select(AccountStatusLabel).where(AccountStatusLabel.status_created_at < end_date)
        if start_date is not None:
            query = query.where(AccountStatusLabel.status_created_at >= start_date)
            total_query = total_query.where(AccountStatusLabel.status_created_at >= start_date)
        
        table = create_entities_table(name.replace("-", "_"), db)
        db_uri = db.get_bind().url.render_as_string(hide_password=False)
        feature_views = get_feature_views(fs)
        total = db.scalar(total_query)

        start = time.time()

        ddf = dd.read_sql_query(
            sql=query,
            con=db_uri,
            index_col="author_id",
            bytes_per_chunk="64 MiB",
            meta=pd.DataFrame({
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
            })
        )
        
        with ProgressBar():
            ddf.map_partitions(InsertPositives(db, table)).compute()
        db.commit()

        print(f"Duration = {time.time()-start}")

        # sample negatives from statuses of engaged author
        negative_samplers = [
            EngagedAuthorNegativeSampler(db, table),
            FollowingNegativeSampler(db, table),
            RandomNegativeSampler(db, table),
        ]
        
        for sampler in negative_samplers:
            print(f"Start sampling {sampler}")
            with utils.duration("Sampled negatives in {:.3f} seconds."):
                sampler()

        with utils.duration("Fetched historical features in {:.3f} seconds."):
            df = get_historical_features(
                entity_table=table.name,
                feature_views=feature_views,
                db=db
            ).fillna(0)
    
        db.exec(text(f"DROP TABLE IF EXISTS {table.name};"))
        
        return df

# class NegativeSampler:
#     def __init__(self, positives):
#         self.positives = positives
#         self.reset()

#     def reset(self):
#         self.unique_pairs = set([tuple(p) for p in self.positives[['account_id', 'status_id']].drop_duplicates().values.tolist()])
    
#     def __call__(self, n, db, table):
#         bar = tqdm(desc="Negatives", total=n)

#         n_misses = 0
#         n_negatives = 0

#         while n_negatives < n:
#             account_id = self.positives['account_id'].sample(1).values[0]
#             status_id, author_id, event_time = self.positives.sample(1).values[0, 1:]

#             if (account_id, status_id) in self.unique_pairs:
#                 n_misses += 1
#                 if n_misses > 10:
#                     break
#                 continue

#             n_misses = 0
#             n_negatives += 1
            
#             self.unique_pairs.add((account_id, status_id))

#             db.exec(insert(table).values(
#                 account_id=account_id,
#                 status_id=status_id,
#                 author_id=author_id,
#                 time=event_time,
#             ))
#             bar.update(1)

#         db.commit()
