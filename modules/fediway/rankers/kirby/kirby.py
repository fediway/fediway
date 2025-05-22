import json
import pickle

import numpy as np
import pandas as pd
from pathlib import Path
from lightgbm import LGBMClassifier, Booster
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from ..base import Ranker
from .features import LABELS
from .scalers import get_scaler


class Kirby(Ranker):
    label: str
    model: BaseEstimator

    MODELS = [
        "linear",
        "random_forest",
        "xgboost",
        "lightgbm",
    ]

    def __init__(
        self,
        model: BaseEstimator,
        scaler: TransformerMixin,
        features: list[str],
        labels: list[str] = LABELS,
        version="v0.1",
    ):
        self.features = features
        self.labels = labels
        self.model = model
        self.scaler = scaler
        self.version = version
        self.label_weights = np.ones(len(labels)) / len(labels)

    @property
    def name(self) -> str:
        return f"kirby-{self.version}"

    @classmethod
    def linear(
        cls,
        features: list[str],
        labels: list[str],
        scaler: str = "standard",
        max_iter: int = 1000,
        random_state: int = None,
    ):
        model = LogisticRegression(max_iter=max_iter)
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, labels)

    @classmethod
    def random_forest(
        cls,
        features: list[str],
        labels: str,
        scaler: str = "standard",
        n_estimators: int = 1500,
        random_state: int = None,
    ):
        model = RandomForestClassifier(n_estimators=n_estimators)
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, labels)

    @classmethod
    def xgboost(
        cls,
        features: list[str],
        labels: list[str],
        scaler: str = "standard",
        random_state: int = None,
    ):
        from xgboost import XGBClassifier

        model = XGBClassifier(
            objective="multi:softprob",
            num_class=len(labels),
        )
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, labels)

    @classmethod
    def lightgbm(
        cls,
        features: list[str],
        labels: list[str],
        num_leaves: int = 32,
        max_depth: int = 6,
        scaler: str = "standard",
        n_estimators: int = 1000,
        random_state: int = None,
        n_jobs: int = -1,
    ):
        model = LGBMClassifier(
            objective="multiclass",
            num_class=len(labels),
            metric="multi_logloss",
            n_estimators=n_estimators,
            num_leaves=num_leaves,
            learning_rate=0.1,
            max_depth=max_depth,
            n_jobs=n_jobs,
        )
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, labels)

    def train(self, dataset: pd.DataFrame):
        X = self.scaler.fit_transform(dataset[self.features].values)
        y = np.argmax(dataset[self.labels].values.astype(int), axis=1)

        self.model.fit(X, y)

    def predict_proba(self, dataset: pd.DataFrame):
        X = dataset[self.features].values
        X = self.scaler.transform(X)
        return self.model.predict_proba(X)

    def predict(self, dataset: pd.DataFrame):
        return (self.predict_proba(dataset) * self.label_weights).sum(axis=1)

    def evaluate(self, dataset: pd.DataFrame):
        y_true_all = dataset[self.labels].values.astype(int)
        y_pred_all = self.predict_proba(dataset)

        results = {}

        for label, y_pred, y_true in zip(self.labels, y_pred_all.T, y_true_all.T):
            auroc = roc_auc_score(y_true, y_pred)
            results[label] = {"auroc": auroc}

        return results

    def save(self, path: Path | str):
        if type(path) != Path:
            path = Path(path)

        with open(path / "model.pkl", "wb") as f:
            pickle.dump(self.model, f)

        with open(path / "scaler.pkl", "wb") as f:
            pickle.dump(self.scaler, f)

        with open(path / "params.json", "w") as f:
            json.dump(
                {
                    "features": self.features,
                    "labels": self.labels,
                    "version": self.version,
                },
                f,
                indent=4,
            )

    @classmethod
    def load(cls, path: Path | str):
        if type(path) != Path:
            path = Path(path)

        with open(path / "model.pkl", "rb") as f:
            model = pickle.load(f)

        with open(path / "scaler.pkl", "rb") as f:
            scaler = pickle.load(f)

        with open(path / "params.json", "r") as f:
            params = json.load(f)

        return cls(model, scaler, **params)
