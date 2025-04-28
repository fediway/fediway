
from feast import FeatureStore
import pandas as pd

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
from modules.fediway.models import AccountStatusLabel
from app.features.offline_fs import get_historical_features

LABEL2ID = {
    'favourite': 1,
    'reblog': 2,
    'reply': 3,
}

class RankerV1Dataset(Dataset):
    @classmethod
    def extract(cls, fs: FeatureStore, db: Session, name: str):
        query = (
            select(AccountStatusLabel)
        )

        table = Table(name.replace("-", "_"), MetaData(),
            Column('account_id', BigInteger, primary_key=True),
            Column('status_id', BigInteger, primary_key=True),
            Column('author_id', BigInteger, primary_key=True),
            Column('time', DateTime),
        )

        # db.exec(text(f"DROP TABLE IF EXISTS {table.name};"))
        # db.exec(text(
        #     utils.compile_sql(CreateTable(table))
        #     .replace(" NOT NULL", "")
        #     .replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
        # ))
        
        # pos_entites = 0
        # neg_entities = 0
        # lookup = set()
        # account_ids = []
        # statuses = []
        # for label in tqdm(db.exec(query).yield_per(100)):
        #     lookup.add((label.account_id, label.status_id))
        #     pos_entites += 1
        #     db.exec(insert(table).values(
        #         account_id=label.account_id,
        #         status_id=label.status_id,
        #         author_id=label.author_id,
        #         time=label.status_created_at,
        #     ))
        #     account_ids.append(label.account_id)
        #     statuses.append((label.status_id, label.author_id, label.status_created_at))
        
        # misses = 0
        # while neg_entities < pos_entites * 4:
        #     account_id = random.choice(account_ids)
        #     status_id, author_id, event_time = random.choice(statuses)

        #     if (account_id, status_id) in lookup:
        #         misses += 1
        #         if misses > 10:
        #             break
        #         continue

        #     misses = 0
        #     neg_entities += 1
            
        #     lookup.add((account_id, status_id))
        #     db.exec(insert(table).values(
        #         account_id=account_id,
        #         status_id=status_id,
        #         author_id=author_id,
        #         time=event_time,
        #     ))
        # db.commit()
        # exit()

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

        with utils.duration("Fetched historical features in {:.3f} seconds."):
            df = get_historical_features(
                entity_table=table.name,
                feature_views=feature_views,
                db=db
            ).fillna(0)
        # db.exec(text(f"DROP TABLE IF EXISTS {table.name};"))
        # print(df)
        # exit()
        
        return Dataset.from_pandas(df)


# fv_select = f"""
#         (
#             select ARRAY[{schema_select_clause}]
#             from {table} f 
#             where {entities_and_clause} and f.event_time = latest.event_time
#             limit 1
#         ) as {fv.name}
#         """
#         columns = []
#         for _fv in feature_views:
#             if _fv.name == fv.name:
#                 columns.append(fv_select)
#             else:
#                 columns.append(f"NULL AS {_fv.name}")
#         columns = ', '.join(columns)        

#         query = f"""
#         select 
#             ds.account_id,
#             ds.status_id,
#             {columns}
#         from {entity_table} ds
#         join (
#             select max(f.event_time) as event_time, {entities_select_clause}
#             from {table} f 
#             join {entity_table} ds
#             on {entities_and_clause} and f.event_time < ds.time
#             group by {entities_select_clause}
#         ) as latest
#         on {entities_and_clause.replace('f', 'latest')}
#         """