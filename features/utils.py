import operator
from datetime import timedelta
from functools import reduce

import pyarrow as pa

# from feast.infra.offline_stores.contrib.spark_offline_store.spark_source import SparkSource
from feast import Entity, FeatureView, Field, KafkaSource, PushSource
from feast.data_format import JsonFormat
from feast.types import (
    Array,
    Bool,
    Bytes,
    FeastType,
    Float32,
    Float64,
    Int32,
    Int64,
    String,
    UnixTimestamp,
)

from modules.features.sources import RisingWaveSource


def make_feature_view(
    name: str,
    entities: list[Entity],
    schema: list[Field],
    online: bool = True,
    ttl=timedelta(days=365),
    tags={},
) -> FeatureView:
    fv = FeatureView(
        name=name,
        entities=entities,
        ttl=ttl,
        schema=schema,
        online=online,
        source=get_source(view_name=name, schema=schema),
        tags=tags,
    )

    return fv


def flatten(arr):
    return reduce(operator.add, arr)


def _feast_type_to_pa_type(dtype: FeastType):
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

    if isinstance(dtype, Array):
        return pa.list_(_feast_type_to_pa_type(dtype.base_type))

    return type_mapping[dtype]


def _feast_type_to_json_type(dtype: FeastType):
    type_mapping = {
        Int64: "int",
        Int32: "int",
        Float32: "float",
        Float64: "float",
        String: "string",
        Bytes: "string",
        Bool: "bool",
        UnixTimestamp: "timestamp",
    }

    return type_mapping[dtype]


def _schema_to_json_format(schema: list[Field]) -> JsonFormat:
    return JsonFormat(
        schema_json=", ".join(
            [f"{field.name} {_feast_type_to_json_type(field.dtype)}" for field in schema]
        )
    )


def get_source(view_name: str, schema: list[Field]) -> KafkaSource:
    batch_source = RisingWaveSource(
        name=f"{view_name}_offline_store",
        table=f"offline_features_{view_name}",
        timestamp_field="event_time",
    )

    return PushSource(
        name=f"{view_name}_stream",
        batch_source=batch_source,
    )
