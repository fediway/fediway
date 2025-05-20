from feast import FeatureStore

from config import config

feature_store = FeatureStore(config=config.feast.repo_config)


def get_feature_store():
    return feature_store
