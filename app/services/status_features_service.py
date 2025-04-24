
from feast import FeatureStore
from datetime import datetime
from fastapi import Depends
import pandas as pd
import numpy as np
from loguru import logger
import time

from app.core.feast import get_feature_store
from app.modules.models import Status, StatusStats
from modules.fediway.feed.features import Features

class StatusFeaturesService(Features):
    # cache: pd.DataFrame

    def __init__(self, fs: FeatureStore = Depends(get_feature_store)):
        self.fs = fs

    def get(self, candidates: list[str | int], features: list[str]) -> np.ndarray | None:        
        if len(features) == 0:
            return []

        if len(candidates) == 0:
            return []

        start = time.time()

        data = self.fs.get_online_features(
            features=features,
            entity_rows=[{'status_id': c} for c in candidates]
        ).to_df().values

        logger.info(f"Fetched features for {len(candidates)} statuses in {int((time.time() - start) * 1000)} milliseconds.")

        return data