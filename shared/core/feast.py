from config import config

try:
    from feast import FeatureStore

    feature_store = FeatureStore(config=config.feast.repo_config)
except ImportError:
    FeatureStore = None
    feature_store = None


def get_feature_store():
    if feature_store is None:
        raise ImportError("Feast is not installed. Install with: uv sync --extra features")
    return feature_store
