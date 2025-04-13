
from tqdm import tqdm
from sqlmodel import Session, func, select, exists
from sqlmodel.sql._expression_select_cls import Select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import label
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

                    'interactions.a_replied_b',
                    'interactions.b_replied_a',
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
                Select(Account.id)
                .where(Account.id == Status.account_id)
                .where((
                    exists()
                    .where(Favourite.status_id == int(row['id']))
                    .where(Favourite.account_id == Account.id)
                ))
                .group_by(Account.id, Status.account_id)
            )

            for f in features:
                if f.startswith('interactions'):
                    positive_query = FEATURES[f].query(positive_query, Account.id, Status.account_id)

            fav_accounts = db.exec(positive_query).mappings().all()

            negative_query = (
                Select(Account.id)
                .where((
                    ~exists()
                    .where(Favourite.status_id == row['id'])
                    .where(Favourite.account_id == Account.id)
                ))
                .where((
                    exists()
                    .where(Status.account_id == Account.id)
                    .where(Status.language == row['language'])
                ))
                .order_by(func.random())
                .limit(len(fav_accounts))
                .group_by(Account.id)
            )

            for f in features:
                if f.startswith('interactions'):
                    negative_query = FEATURES[f].query(negative_query, Account.id, Status.account_id)
            
            fav_controls = db.exec(negative_query).mappings().all()

            for account, is_favourited in (
                list(zip(fav_accounts, [1 for _ in range(len(fav_accounts))])) + 
                list(zip(fav_controls, [0 for _ in range(len(fav_controls))]))
                ):

                # print(account)
                # exit()

                account_feats = {f: FEATURES[f].get(**account) for f in features if not f.startswith('status')}
                dataset_dict['status_id'].append(row['id'])

                for f in features:
                    if f.startswith('status'):
                        dataset_dict[f"feat.{f}"].append(status_feats[f])
                    if f.startswith('interactions'):
                        dataset_dict[f"feat.{f}"].append(account_feats[f])

                # dataset_dict['status.age_in_seconds'].append(status_age_in_seconds)
                # dataset_dict['status.favourites_count'].append(row.StatusStats.favourites_count)
                # dataset_dict['status.reblogs_count'].append(row.StatusStats.reblogs_count)
                # dataset_dict['status.replies_count'].append(row.StatusStats.replies_count)
                # dataset_dict['status.num_images'].append(num_images)
                # dataset_dict['status.num_gifs'].append(num_gifs)
                # dataset_dict['status.num_videos'].append(num_videos)
                # dataset_dict['status.num_tags'].append(row.num_tags)
                # dataset_dict['status.num_mentions'].append(row.num_mentions)
                dataset_dict['label.is_favourited'].append(is_favourited)
                # dataset_dict['status.is_reblogged'].append(0)
                # dataset_dict['status.is_replied'].append(0)
            
            bar.update(1)

        bar.close()

        return cls.from_dict(dataset_dict)