
from feast import FeatureStore
from dask import dataframe as dd
from dask import array as da
from dask.distributed import Client, as_completed
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
from datetime import datetime, timedelta
from datasets import Dataset
from tqdm import tqdm

import app.utils as utils
from .utils import create_dataset_table
from modules.fediway.models import AccountStatusLabel
from app.features.offline_fs import get_historical_features

class InsertAndMapPositives:
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
        
        return labels[['account_id', 'status_id', 'status_created_at']]

    def __dask_tokenize__(self):
        return normalize_token(type(self)), self.table.name
    
class RankerV1Dataset(Dataset):
    @classmethod
    def extract(cls, fs: FeatureStore, db: Session, name: str):
        feature_views = [
            'author_engagement_all',
            'author_engagement_is_favourite',
            'author_engagement_is_reblog',
            'author_engagement_is_reply',
            'author_engagement_has_image',
            'author_engagement_has_gifv',
            'author_engagement_has_video',
            'account_engagement_all',
            'account_engagement_is_favourite',
            'account_engagement_is_reblog',
            'account_engagement_is_reply',
            'account_engagement_has_image',
            'account_engagement_has_gifv',
            'account_engagement_has_video',
            'account_author_engagement_all',
            'account_author_engagement_is_favourite',
            'account_author_engagement_is_reblog',
            'account_author_engagement_is_reply',
            'account_author_engagement_has_image',
            'account_author_engagement_has_gifv',
            'account_author_engagement_has_video',
        ]

        feature_views = [
            fs.get_feature_view(fv) for fv in feature_views
        ]

        query = (
            select(AccountStatusLabel)
        )

        # create dataset table
        table = create_dataset_table(name.replace("-", "_"), db)
        db_uri = db.get_bind().url.render_as_string(hide_password=False)
        db.commit()

        start = time.time()

        ddf = dd.read_sql_query(
            sql=query,
            con=db_uri,
            index_col="author_id",
            npartitions=10,
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
        
        positives = (
            ddf.map_partitions(InsertAndMapPositives(db, table))
            .compute()
            .reset_index()
            .rename(columns={'status_created_at': 'time'})
        )

        # account_ids = positives['account_id'].values
        # statuses = positives[['status_id', 'author_id', 'time']].values
        # unique_pairs = set([tuple(p) for p in positives[['account_id', 'status_id']].drop_duplicates().values.tolist()])
        db.commit()

        print(f"Duration = {time.time()-start}")

        # client = Client(n_workers=4, threads_per_worker=1, memory_limit='8GB')

        ipsm = DistributedIPSM(
            positives, 
            NegativeSampler(positives),
            feature_views,
            db=db,
            table=table,
        )

        # generate initial matches
        ipsm.iterative_matching()

        exit()

        

        with utils.duration("Fetched historical features in {:.3f} seconds."):
            df = get_historical_features(
                entity_table=table.name,
                feature_views=feature_views,
                db=db
            ).fillna(0)
    
        db.exec(text(f"DROP TABLE IF EXISTS {table.name};"))
        
        return Dataset.from_pandas(df)

class NegativeSampler:
    def __init__(self, positives):
        self.positives = positives
        self.reset()

    def reset(self):
        self.unique_pairs = set([tuple(p) for p in self.positives[['account_id', 'status_id']].drop_duplicates().values.tolist()])
    
    def __call__(self, n, db, table):
        bar = tqdm(desc="Negatives", total=n)

        n_misses = 0
        n_negatives = 0

        while n_negatives < n:
            account_id = self.positives['account_id'].sample(1).values[0]
            status_id, author_id, event_time = self.positives.sample(1).values[0, 1:]

            if (account_id, status_id) in self.unique_pairs:
                n_misses += 1
                if n_misses > 10:
                    break
                continue

            n_misses = 0
            n_negatives += 1
            
            self.unique_pairs.add((account_id, status_id))

            db.exec(insert(table).values(
                account_id=account_id,
                status_id=status_id,
                author_id=author_id,
                time=event_time,
            ))
            bar.update(1)

        db.commit()

def mahalanobis_distance(mu_t, mu_c, sigma_c_inv):
    delta = mu_t - mu_c
    return delta.T @ sigma_c_inv @ delta

def incremental_mean(old_mean, n, x_old, x_new):
    return old_mean + (x_new - x_old) / n

def incremental_covariance(old_cov, old_mean, n, x_old, x_new):
    delta_old = x_old - old_mean
    delta_new = x_new - old_mean
    return old_cov + (np.outer(delta_new, delta_new) - np.outer(delta_old, delta_old)) / (n - 1)

class DistributedIPSM:
    '''
    Distributed Iterative Propensity Score Matching.
    '''

    def __init__(self, positives, negative_sampler, feature_views, db, table, batch_size=1_000, caliper=0.1):
        self.positives = positives
        self.batch_size = batch_size
        self.negative_sampler = negative_sampler
        self.db = db
        self.p_table = table
        self.n_table = create_dataset_table(table.name+"_negatives", db)
        self.feature_views = feature_views
        self.caliper = caliper
        self.matches = None
        self.model = None

        self.df_pos = self._get_features(self.p_table)
        self.features = [c for c in self.df_pos.columns if '__' in c]
        self.mu_p = np.mean(self.df_pos[self.features].values, axis=0)

    def _get_features(self, table):
        with utils.duration("Fetched historical features in {:.3f} seconds."):
            return get_historical_features(
                entity_table=table.name,
                feature_views=self.feature_views,
                db=self.db
            ).fillna(0)
        
    def initial_sample(self):
        self.negative_sampler(len(self.positives), self.db, self.n_table)
        self.df_neg = self._get_features(self.n_table)
        
        self.mu_n = np.mean(self.df_neg[self.features].values, axis=0)
        self.sigma_n = np.cov(self.df_neg[self.features], rowvar=False)
        self.sigma_n_inv = np.linalg.pinv(self.sigma_n)
        self.md = mahalanobis_distance(self.mu_p, self.mu_n, self.sigma_n_inv)

    def compute_mean_smd(self, pos, neg):
        pos = pos[columns]
        neg = neg[columns]
        smds = (pos.mean() - neg.mean()) / np.sqrt((pos.var() + neg.var())/2)
        return np.nanmean(smds.values)
        
    def train_propensity_model(self):
        

        print("SMD", self.compute_mean_smd(df_pos, df_neg))

        df = pd.concat([df_pos, df_neg], axis=0)

        X = df[[c for c in df.columns if "__" in c]].values
        y = df['label.is_favourited'].values.astype(int)
        self.scaler = MinMaxScaler()

        X = self.scaler.fit_transform(X)
        
        self.model = DaskXGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            verbosity=1
        )
        
        # Distributed training
        self.model.fit(X, y)
        
        from sklearn.metrics import roc_auc_score
        y_pred = self.model.predict_proba(X)[:, 1]
        auroc = roc_auc_score(y, y_pred)
        print("Auroc", auroc)

        return self.model
    
    def find_better_matches(self, batch):
        """Find better matches in a control batch using Dask"""
        # Compute propensity scores
        ps_batch = self.model.predict_proba(batch.values)[:, 1]
        ps_matches = self.model.predict_proba(self.matches.values)[:, 1]
        
        # Calculate distances
        distances = da.sqrt(
            (ps_batch[:, None] - ps_matches[None, :])**2
        )
        
        # Find improvements within caliper
        improvements = da.argmin(
            da.where(distances < self.caliper, distances, np.inf),
            axis=1
        )

        exit()
        
        # Update matches
        new_matches = batch[da.any(improvements != -1, axis=1)]
        return new_matches.compute_chunk_sizes()
    
    def iterative_matching(self, n_iter=10):
        self.initial_sample()
        print("mahalanobis_distance", self.md)

        nn_table = create_dataset_table(self.p_table.name+"_new_negatives", self.db)
        batch_size = 10
        
        for i in range(n_iter):
            self.db.exec(text(f"DELETE FROM {nn_table.name};"))
            self.negative_sampler(batch_size, self.db, nn_table)
            time.sleep(1.0)
            self.db.commit()
            df_new = self._get_features(nn_table)
            df_old = self.df_neg.sample(batch_size)

            x_new = df_new[self.features].values
            x_old = df_old[self.features].values
            mu_n_new = incremental_mean(self.mu_n, len(self.df_neg), x_old, x_new)
            sigma_n_new = incremental_covariance(self.sigma_n, self.mu_n, len(self.df_neg), x_old, x_new)
            sigma_n_inv_new = np.linalg.pinv(sigma_n_new)

            md_new = mahalanobis_distance(self.mu_p, mu_n_new, sigma_n_inv_new)
            print(md_new)
            exit()
            
            # if delta_D > best_delta:
            #     best_delta = delta_D
            #     best_swap = (x_old, x_new)

            
            # Check balance
            self.check_balance()
            
    def check_balance(self):
        """Calculate standardized mean differences using Dask"""
        treated_mean = self.treated.mean().compute()
        control_mean = self.matches.mean().compute()
        
        treated_var = self.treated.var().compute()
        control_var = self.matches.var().compute()
        
        smd = (treated_mean - control_mean) / np.sqrt(
            (treated_var + control_var) / 2
        )
        print(f"Current SMD: {smd.abs().mean():.4f}")