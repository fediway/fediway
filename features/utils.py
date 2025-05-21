import operator
from datetime import timedelta
from functools import reduce

import pyarrow as pa

# from feast.infra.offline_stores.contrib.spark_offline_store.spark_source import SparkSource
from feast import Entity, FeatureView, Field, PushSource
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
    PostgreSQLSource,
)
from feast.types import (
    Array,
    Bool,
    Bytes,
    Float32,
    Float64,
    Int32,
    Int64,
    String,
    UnixTimestamp,
)


def make_feature_view(
    name: str,
    entities: list[Entity],
    schema: list[Field],
    offline_store_path: str,
    online: bool = True,
    ttl=timedelta(days=365),
) -> FeatureView:
    source = get_push_source(
        view_name=name,
        offline_store_path=offline_store_path,
    )

    fv = FeatureView(
        name=name,
        entities=entities,
        ttl=ttl,
        schema=schema,
        online=online,
        source=source,
    )

    return fv


def flatten(arr):
    return reduce(operator.add, arr)


def _feast_type_to_pa_type(_type):
    type_mapping = {
        Int64: pa.int64(),
        Int32: pa.int32(),
        Float32: pa.float32(),
        Float64: pa.float64(),
        String: pa.string(),
        Bytes: pa.binary(),
        Bool: pa.bool_(),
        UnixTimestamp: pa.timestamp("s"),
    }

    if isinstance(_type, Array):
        return pa.list_(_feast_type_to_pa_type(_type.base_type))

    return type_mapping[_type]


def get_push_source(view_name: str, offline_store_path: str) -> PushSource:
    # batch_source = SparkSource(
    #     name=f"{view_name}_source",
    #     path=f"{offline_store_path}/{view_name}",
    #     file_format="parquet",
    #     timestamp_field="event_time",
    #     date_partition_column="date"
    # )

    batch_source = PostgreSQLSource(
        name=f"{view_name}_source",
        table=f"offline_fs_{view_name}_features",
        timestamp_field="event_time",
    )

    push_source = PushSource(
        name=f"{view_name}_stream",
        batch_source=batch_source,
    )

    return push_source
