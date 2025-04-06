
from tqdm import tqdm
from sqlmodel import Session, func, select, exists
from sqlalchemy.orm import selectinload
from datetime import datetime
from datasets import Dataset

from modules.utils import string
from app.modules.models import Favourite, Account, Status, StatusStats, MediaAttachment, Mention, Tag, StatusTag
from app.utils import sql_string

class LightRankerDataset(Dataset):
    @classmethod
    def extract(cls, db: Session, chunk_size: 100):
        query = (
            select(
                Status, 
                StatusStats, 
                func.count(StatusTag.status_id).label("num_tags"),
                func.count(Mention.status_id).label("num_mentions"),
            )
            .outerjoin(Status.media_attachments)
            .outerjoin(Mention, Status.id == Mention.status_id)
            .outerjoin(StatusTag, Status.id == StatusTag.status_id)
            .where(Status.id == StatusStats.status_id)
            .where(exists().where(Favourite.status_id == Status.id))
            .group_by(*Status.__table__.columns, *StatusStats.__table__.columns)
            .options(selectinload(Status.media_attachments))
        )

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
            'language': [],
            'status_age_in_seconds': [],
            'favourites_count': [],
            'reblogs_count': [],
            'replies_count': [],
            'num_images': [],
            'num_videos': [],
            'num_gifs': [],
            'num_tags': [],
            'num_mentions': [],

            # labels
            'is_favourited': [],
            'is_reblogged': [],
            'is_replied': [], 
        }

        now = datetime.now()

        for row in rows:
            status_age_in_seconds = (now - row.Status.created_at).seconds
            num_images = sum([m.type == 0 for m in row.Status.media_attachments])
            num_gifs = sum([m.type == 1 for m in row.Status.media_attachments])
            num_videos = sum([m.type == 4 for m in row.Status.media_attachments])

            fav_accounts = db.exec(
                select(Account)
                .where((
                    exists()
                    .where(Favourite.status_id == row.Status.id)
                    .where(Favourite.account_id == Account.id)
                ))
            ).all()
            fav_controls = db.exec((
                select(Account)
                .where((
                    ~exists()
                    .where(Favourite.status_id == row.Status.id)
                    .where(Favourite.account_id == Account.id)
                ))
                .order_by(func.random())
                .limit(len(fav_accounts))
            )).all()

            for account, is_favourited in (
                list(zip(fav_accounts, [1 for _ in range(len(fav_accounts))])) + 
                list(zip(fav_controls, [0 for _ in range(len(fav_controls))]))
                ):

                dataset_dict['language'].append(row.Status.language)
                dataset_dict['status_age_in_seconds'].append(status_age_in_seconds)
                dataset_dict['favourites_count'].append(row.StatusStats.favourites_count)
                dataset_dict['reblogs_count'].append(row.StatusStats.reblogs_count)
                dataset_dict['replies_count'].append(row.StatusStats.replies_count)
                dataset_dict['num_images'].append(num_images)
                dataset_dict['num_gifs'].append(num_gifs)
                dataset_dict['num_videos'].append(num_videos)
                dataset_dict['num_tags'].append(row.num_tags)
                dataset_dict['num_mentions'].append(row.num_mentions)
                dataset_dict['is_favourited'].append(is_favourited)
                dataset_dict['is_reblogged'].append(0)
                dataset_dict['is_replied'].append(0)
            
            bar.update(1)

        bar.close()

        return cls.from_dict(dataset_dict)