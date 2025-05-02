
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import roc_auc_score

from .scalers import get_scaler
from .features import LABELS

class Kirby():
    label: str
    model: BaseEstimator

    MODELS = [
        'linear',
        'random_forest',
        'xgboost',
        'lightgbm',
    ]

    def __init__(self, 
                 model: BaseEstimator, 
                 scaler: TransformerMixin, 
                 features: list[str], 
                 labels: list[str] = LABELS):
        self.features = features
        self.labels = labels
        self.model = model
        self.scaler = scaler

    @classmethod
    def linear(cls, 
               features: list[str], 
               labels: list[str], 
               scaler: str = 'standard', 
               max_iter: int = 1000, 
               random_state: int = None):
        model = LogisticRegression(max_iter=max_iter)
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, labels)

    @classmethod
    def random_forest(cls, 
                      features: list[str], 
                      labels: str, 
                      scaler: str = 'standard', 
                      n_estimators: int = 1500, 
                      random_state: int = None):
        model = RandomForestClassifier(n_estimators=n_estimators)
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, labels)

    @classmethod
    def xgboost(cls, 
                features: list[str], 
                labels: list[str], 
                scaler: str = 'standard', 
                random_state: int = None):
        from xgboost import XGBClassifier

        model = XGBClassifier(
            objective='multi:softprob',
            num_class=len(labels),
        )
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, labels)

    @classmethod
    def lightgbm(cls, 
                 features: list[str], 
                 labels: list[str], 
                 scaler: str = 'standard', 
                 n_estimators: int = 1000, 
                 random_state: int = None):
        from lightgbm import LGBMClassifier

        model = LGBMClassifier(
            objective='multiclass',
            num_class=len(labels),
            metric='multi_logloss',
            n_estimators=n_estimators,
            num_leaves=50,
            learning_rate=0.1,
            max_depth=10
        )
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, labels)

    def train(self, dataset: pd.DataFrame):
        X = self.scaler.fit_transform(dataset[self.features].values)
        y = np.argmax(dataset[self.labels].values, axis=1)

        self.model.fit(X, y)

    def predict_proba(self, dataset: pd.DataFrame):
        X = dataset[self.features].values
        X = self.scaler.transform(X)
        return self.model.predict_proba(X)

    def evaluate(self, dataset: pd.DataFrame):
        y_true_all = dataset[self.labels].values
        y_pred_all = self.predict_proba(dataset)

        results = {}

        for label, y_pred, y_true in zip(self.labels, y_pred_all.T, y_true_all.T):
            auroc = roc_auc_score(y_true, y_pred)
            results[label] = {'auroc': auroc}

        return results