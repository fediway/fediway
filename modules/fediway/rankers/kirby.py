
import numpy as np
from datasets import Dataset
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import roc_auc_score

from .scalers import get_scaler

class Kirby():
    label: str
    model: BaseEstimator

    MODELS = [
        'linear',
        'random_forest',
        'xgboost'
    ]

    def __init__(self, 
                 model: BaseEstimator, 
                 scaler: TransformerMixin, 
                 features: list[str], 
                 label: str):
        self.features = features
        self.label = label
        self.model = model
        self.scaler = scaler

    @classmethod
    def linear(cls, 
               features: list[str], 
               label: str, 
               scaler: str = 'standard', 
               max_iter: int = 1000, 
               random_state: int = None):
        model = LogisticRegression(max_iter=max_iter)
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, label)

    @classmethod
    def random_forest(cls, 
                      features: list[str], 
                      label: str, 
                      scaler: str = 'standard', 
                      n_estimators: int = 1000, 
                      random_state: int = None):
        model = RandomForestClassifier(n_estimators=n_estimators)
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, label)

    @classmethod
    def xgboost(cls, 
                      features: list[str], 
                      label: str, 
                      scaler: str = 'standard', 
                      random_state: int = None):
        from xgboost import XGBClassifier
        model = XGBClassifier()
        scaler = get_scaler(scaler)

        return cls(model, scaler, features, label)

    def train(self, dataset: Dataset):
        X = np.array([dataset[f] for f in self.features]).T
        X = self.scaler.fit_transform(X)
        y = np.array(dataset[self.label])

        self.model.fit(X, y)

    def predict_proba(self, X):
        X = self.scaler.transform(X)
        return self.model.predict_proba(X)[:, 1]

    def evaluate(self, dataset: Dataset):
        X = np.array([dataset[f] for f in self.features]).T
        X = self.scaler.transform(X)
        y_true = np.array(dataset[self.label])
        y_pred = self.model.predict_proba(X)[:, 1]

        auroc = roc_auc_score(y_true, y_pred)

        return {'auroc': auroc}