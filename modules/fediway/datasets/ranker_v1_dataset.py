
from feast import FeatureStore
import pandas as pd

import random
from tqdm import tqdm
from sqlmodel import Session, func, select, exists
from sqlmodel.sql._expression_select_cls import Select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import label, and_
from datetime import datetime, timedelta
from datasets import Dataset

import app.utils as utils
from modules.fediway.models import StatusEngagement

LABEL2ID = {
    'favourite': 1,
    'reblog': 2,
    'reply': 3,
}

class RankerV1Dataset(Dataset):
    @classmethod
    def extract(cls, fs: FeatureStore, rw: Session):
        query = select(StatusEngagement).filter(StatusEngagement.type == 'favourite')
        
        labels = []
        pos_entites = []
        neg_entities = []
        lookup = set()
        account_ids = []
        author_ids = []
        for engagement in rw.exec(query).yield_per(100):
            lookup.add((engagement.account_id, engagement.author_id))
            pos_entites.append((
                engagement.account_id,
                engagement.author_id,
                engagement.status_event_time
            ))
            account_ids.append(engagement.account_id)
            author_ids.append((engagement.author_id, engagement.status_event_time))
            labels.append(1)
        
        while len(neg_entities) < len(pos_entites) * 2:
            account_id = random.choice(account_ids)
            author_id, event_time = random.choice(author_ids)

            if (account_id, author_id) in lookup:
                continue
            
            lookup.add((account_id, author_id))
            neg_entities.append((account_id, author_id, event_time))
            labels.append(0)

        entities_df = pd.DataFrame(pos_entites + neg_entities, columns=['account_id', 'author_id', 'event_timestamp'])

        with utils.duration("Fetched historical features in {:.3f} seconds."):
            data = fs.get_historical_features(
                features=fs.get_feature_service("ranker"),
                entity_df=entities_df
            ).to_df().fillna(0)
        
        data = data[data.columns[3:]]
        data['label.is_favourited'] = labels
        
        return Dataset.from_pandas(data)