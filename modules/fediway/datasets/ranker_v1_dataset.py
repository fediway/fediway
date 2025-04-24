
from feast import FeatureStore
import pandas as pd

import random
from tqdm import tqdm
from sqlmodel import Session, func, select, exists
from sqlmodel.sql._expression_select_cls import Select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.schema import CreateTable
from sqlalchemy import label, and_, text, MetaData, Table, DateTime, Column, Integer, BigInteger, String, Float, insert
from datetime import datetime, timedelta
from datasets import Dataset
from tqdm import tqdm

import app.utils as utils
from modules.fediway.models import StatusEngagement
from app.features.offline_fs import get_historical_features

LABEL2ID = {
    'favourite': 1,
    'reblog': 2,
    'reply': 3,
}

class RankerV1Dataset(Dataset):
    @classmethod
    def extract(cls, fs: FeatureStore, db: Session, name: str):
        query = select(StatusEngagement).filter(StatusEngagement.type == 'reblog')

        table = Table(name.replace("-", "_"), MetaData(),
            Column('account_id', BigInteger, primary_key=True),
            Column('author_id', BigInteger, primary_key=True),
            Column('time', DateTime),
            Column('label', Integer)
        )

        db.exec(text(
            utils.compile_sql(CreateTable(table))
            .replace(" NOT NULL", "")
            .replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
        ))
        
        # pos_entites = 0
        # neg_entities = 0
        # lookup = set()
        # account_ids = []
        # author_ids = []
        # for engagement in tqdm(db.exec(query).yield_per(100)):
        #     lookup.add((engagement.account_id, engagement.author_id))
        #     pos_entites += 1
        #     db.exec(insert(table).values(
        #         account_id=engagement.account_id,
        #         author_id=engagement.author_id,
        #         time=engagement.status_event_time,
        #         label=1
        #     ))
        #     account_ids.append(engagement.account_id)
        #     author_ids.append((engagement.author_id, engagement.status_event_time))
        
        # misses = 0
        # while neg_entities < pos_entites:
        #     account_id = random.choice(account_ids)
        #     author_id, event_time = random.choice(author_ids)

        #     if (account_id, author_id) in lookup:
        #         misses += 1
        #         if misses > 10:
        #             break
        #         continue

        #     misses = 0
            
        #     lookup.add((account_id, author_id))
        #     db.exec(insert(table).values(
        #         account_id=account_id,
        #         author_id=author_id,
        #         time=event_time,
        #         label=0
        #     ))
        # db.commit()

        with utils.duration("Fetched historical features in {:.3f} seconds."):
            df = get_historical_features(
                entity_table=table.name,
                fv=fs.get_feature_view("account_engagement_all"),
                db=db
            ).fillna(0)
        
        return Dataset.from_pandas(df)