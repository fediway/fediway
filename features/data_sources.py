
from feast import (
    FileSource,
    PushSource,
)


account_author_batch_source = FileSource(
    name="account_author_source",
    path=f"../data/account_author.parquet",
    timestamp_field="event_time",
)

account_author_push_source = PushSource(
    name="account_author_features",
    batch_source=account_author_batch_source,
)
