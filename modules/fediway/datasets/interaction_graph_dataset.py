
from tqdm import tqdm
from sqlmodel import Session, func, select, exists
from sqlmodel.sql._expression_select_cls import Select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import label, and_
from datetime import datetime
from datasets import Dataset

from .features import FEATURES
from modules.utils import string
from app.modules.models import Favourite, Account, Status, StatusStats, MediaAttachment, Mention, Tag, StatusTag
from app.utils import sql_string

class InteractionGraphDataset(Dataset):
    @classmethod
    def extract(cls, 
                db: Session, 
                chunk_size: int = 100,
                features = [
                    'status.age_in_seconds',
                    'status.num_images',
                    'status.num_videos',
                    'status.num_gifs',
                    'status.num_tags',
                    'status.num_mentions',
                    'status.num_favourites',
                    'status.num_reblogs',
                    'status.num_replies',

                    'interactions.a2b.has_replied',
                    'interactions.a2b.num_favourites',

                    'interactions.b2a.has_replied',
                    'interactions.b2a.num_favourites',

                    # 'interactions.num_favourites_a2b',
                    # 'interactions.num_favourites_b2a',
                ]):
        
        query = (
            Select(Status.id, Status.language)
            .where(exists().where(Favourite.status_id == Status.id))
            .group_by(Status.id)
        )

        for f in features:
            if f.startswith('status'):
                query = FEATURES[f].query(query)
        
        rows = db.exec(query.execution_options(yield_per=chunk_size))
        total = db.scalar((
            select(func.count(Status.id))
            .where(exists().where(Favourite.status_id == Status.id))
        ))
        
        bar = tqdm(
            desc="Statuses",
            total=total
        )

        dataset_dict = {
            'status_id': [],
            # 'account_id': [],
            'label.is_favourited': [],
        } | {f"feat.{f}": [] for f in features
            # user
            # 'user.favourites_count': [],
            # 'user.num_mentions': [],

            # # author

            # # status
            # 'status.age_in_seconds': [],
            # 'status.favourites_count': [],
            # 'status.reblogs_count': [],
            # 'status.replies_count': [],
            # 'status.num_images': [],
            # 'status.num_videos': [],
            # 'status.num_gifs': [],
            # 'status.num_tags': [],
            # 'status.num_mentions': [],

            # # labels
            # 'is_reblogged': [],
            # 'is_replied': [], 
        }

        now = datetime.now()

        for row in rows.mappings():
            status_feats = {f: FEATURES[f].get(**row) for f in features if f.startswith('status')}

            positive_query = (
                Select(Status.id, Status.account_id)
                .join(Favourite, Favourite.status_id == Status.id)
                .where(Status.id == row['id'])
                .group_by(Status.id, Status.account_id)
            )

            for f in features:
                if f.startswith('interactions.a2b'):
                    positive_query = FEATURES[f.replace('.a2b', '')](Favourite.account_id, Status.account_id).query(positive_query)
                if f.startswith('interactions.b2a'):
                    positive_query = FEATURES[f.replace('.b2a', '')](Status.account_id, Favourite.account_id).query(positive_query)

            fav_accounts = db.exec(positive_query).mappings().all()

            negative_query = (
                Select(Status.id, Account.id)
                .join(Favourite, Favourite.status_id == Status.id)
                .join(Account, Favourite.account_id == Account.id)
                .where(Status.id == row['id'])
                .where(Status.language == row['language'])
                .order_by(func.random())
                .limit(len(fav_accounts))
                .group_by(Status.id, Account.id)
            )

            for f in features:
                if f.startswith('interactions.a2b'):
                    negative_query = FEATURES[f.replace('.a2b', '')](Favourite.account_id, Account.id).query(negative_query)
                if f.startswith('interactions.b2a'):
                    negative_query = FEATURES[f.replace('.b2a', '')](Account.id, Favourite.account_id).query(negative_query)
            
            fav_controls = db.exec(negative_query).mappings().all()

            for account, is_favourited in zip(fav_accounts, [1 for _ in range(len(fav_accounts))]):
                account_feats = {
                    f: FEATURES[f.replace('.a2b', '')](Favourite.account_id, Status.account_id).get(**account) for f in features if f.startswith('interactions.a2b')
                } | {
                    f: FEATURES[f.replace('.b2a', '')](Status.account_id, Favourite.account_id).get(**account) for f in features if f.startswith('interactions.b2a')
                }

                dataset_dict['status_id'].append(row['id'])
                dataset_dict['label.is_favourited'].append(is_favourited)
                for f in features:
                    if f.startswith('status'):
                        dataset_dict[f"feat.{f}"].append(status_feats[f])
                    if f.startswith('interactions'):
                        dataset_dict[f"feat.{f}"].append(account_feats[f])
                

            for account, is_favourited in zip(fav_controls, [0 for _ in range(len(fav_controls))]):
                account_feats = {
                    f: FEATURES[f.replace('.a2b', '')](Favourite.account_id, Account.id).get(**account) for f in features if f.startswith('interactions.a2b')
                } | {
                    f: FEATURES[f.replace('.b2a', '')](Account.id, Favourite.account_id).get(**account) for f in features if f.startswith('interactions.b2a')
                }

                dataset_dict['status_id'].append(row['id'])
                dataset_dict['label.is_favourited'].append(is_favourited)
                for f in features:
                    if f.startswith('status'):
                        dataset_dict[f"feat.{f}"].append(status_feats[f])
                    if f.startswith('interactions'):
                        dataset_dict[f"feat.{f}"].append(account_feats[f])
            
            bar.update(1)

        # feat = 'interactions.a2b.has_replied'
        # print(dataset_dict[f'feat.{feat}'])
        # print(sum(dataset_dict[f'feat.{feat}']))
        # exit()
        bar.close()

        return cls.from_dict(dataset_dict)