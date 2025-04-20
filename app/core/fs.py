
from feast import FeatureStore

from config import config

fs = FeatureStore(repo_path=config.feast.feast_repo_path)

def get_feature_store():
    return fs