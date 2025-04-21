
from feast import Field
from feast.types import Array, Float32

from config import config
from ..entities import account
from ..utils import make_feature_view

account_embedding_features = []
account_embedding_types = [
    'latest_account_favourites_embeddings',
    'latest_account_reblogs_embeddings',
    'latest_account_replies_embeddings',
]

for embedding_type in account_embedding_types:
    schema = [Field(name=f"{embedding_type}.embeddings", dtype=Array(Float32))]

    _fv = make_feature_view(
        embedding_type,
        entities=[account],
        schema=schema,
        online=False,
        offline_store_path=config.feast.feast_offline_store_path
    )

    account_embedding_features.append(_fv)