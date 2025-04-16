
from sqlmodel import Session, select
from datetime import datetime
from fastapi import Depends
import numpy as np
from loguru import logger
import time

from app.core.db import get_db_session
from app.modules.models import Status, StatusStats
from modules.fediway.feed.features import Features

class StatusFeaturesService(Features):
    cache: dict

    def __init__(self, db: Session = Depends(get_db_session)):
        self.db = db
        self.cache = {}

    def _fetch(self, candidates):
        start = time.time()

        rows = self.db.exec(
            select(
                Status.id, 
                Status.account_id,
                Status.created_at,
                StatusStats.favourites_count,
                StatusStats.reblogs_count,
                StatusStats.replies_count,
            )
            .join(StatusStats, StatusStats.status_id == Status.id)
            .where(Status.id.in_(candidates))
        ).all()

        for row in rows:
            self.cache[row.id] = {
                'candidate': row.id,
                'account_id': row.account_id,
                'favourites_count': row.favourites_count,
                'reblogs_count': row.reblogs_count,
                'replies_count': row.replies_count,
                'age_in_seconds': (datetime.now() - row.created_at).total_seconds()
            }

        logger.info(f"Fetched features for {len(candidates)} statuses in {int((time.time() - start) * 1000)} milliseconds.")

    def get(self, candidates: list[str | int], features: list[str] = 'account_id') -> np.ndarray | None:        
        if len(features) == 0:
            return None

        if len(candidates) == 0:
            return None

        if self.cache is not None:
            missing = [c for c in candidates if c not in self.cache]
        else:
            missing = candidates

        if len(missing) > 0:
            self._fetch(missing)
        
        feats = []
        zeros = np.zeros(len(features))
        for c in candidates:
            if c in self.cache:
                feats.append(np.array([self.cache[c][f] for f in features]))
            else:
                feats.append(zeros)

        return np.stack(feats)