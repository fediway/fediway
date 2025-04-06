
from tqdm import tqdm
from sqlmodel import Session, func, select
from sqlalchemy import Select
from datasets import Dataset

from modules.utils import string
from app.utils import sql_string

class StatusesDataset(Dataset):
    @classmethod
    def extract(cls, db: Session, query: Select, chunk_size: 100):
        rows = db.exec(query.execution_options(yield_per=chunk_size))
        total = db.scalar(query.with_only_columns(func.count()).order_by(None))

        bar = tqdm(
            desc="Statuses",
            total=total
        )

        dataset_dict = {
            'id': [],
            'account_id': [],
            'text': [],
            'language': [],
            'favourites_count': [],
            'reblogs_count': [],
            'replies_count': [],
        }

        for row in rows:
            dataset_dict['id'].append(row.Status.id)
            dataset_dict['account_id'].append(row.Status.account_id)
            dataset_dict['text'].append(string.strip_html(row.Status.text))
            dataset_dict['language'].append(row.Status.language)
            dataset_dict['favourites_count'].append(row.StatusStats.favourites_count)
            dataset_dict['reblogs_count'].append(row.StatusStats.reblogs_count)
            dataset_dict['replies_count'].append(row.StatusStats.replies_count)
            bar.update(1)

        bar.close()

        return cls.from_dict(dataset_dict)