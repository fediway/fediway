
from sqlmodel import Session, select
from fastapi import Depends
import numpy as np
import polars as pl

from app.core.db import get_db_session
from app.modules.models import Status, StatusStats
from modules.fediway.feed.features import Features

class StatusFeaturesService(Features):
    cache: pl.DataFrame

    def __init__(self, db: Session = Depends(get_db_session)):
        self.db = db
        self.cache = None

    def _fetch(self, candidates) -> pl.DataFrame:
        rows = self.db.exec(
            select(
                Status.id, 
                Status.account_id,
                StatusStats.favourites_count,
                StatusStats.reblogs_count,
                StatusStats.replies_count,
            )
            .where(Status.id.in_(candidates))
            .where(Status.id == StatusStats.status_id)
        ).all()

        df = pl.DataFrame({
            'candidate': [row.id for row in rows],
            'account_id': [row.account_id for row in rows],
            'favourites_count': [row.favourites_count for row in rows],
            'reblogs_count': [row.reblogs_count for row in rows],
            'replies_count': [row.replies_count for row in rows],
        })

        if self.cache is None:
            self.cache = df 
        else:
            self.cache = self.cache.join(df, on='candidate')

    def get(self, candidates: list[str | int], features: list[str] = 'account_id') -> np.ndarray | None:
        if len(features) == 0:
            return None

        if self.cache is not None:
            missing = pl.DataFrame({
                'candidate': candidates
            }).join(self.cache, on='candidate', how='anti')
        else:
            missing = candidates

        if len(missing) > 0:
            self._fetch(missing)

        feats = {
            row['candidate']: np.array([row[f] for f in features]) for row in (
                self.cache
                .filter(pl.col('candidate').is_in(candidates))
                .select(features + ['candidate'])
                .iter_rows(named=True)
            )
        }

        zeros = np.zeros(len(features))

        return np.stack([
            feats.get(c, zeros) for c in candidates
        ])