
from feast import FeatureView, FileSource, PushSource, Entity, Field
from feast.data_format import ParquetFormat
from feast.types import (
    Int64, Float32, Float64, String, Bytes, Bool, Int32, UnixTimestamp, Array
)

import pyarrow as pa
from pyarrow.parquet import ParquetDataset, write_table
from datetime import timedelta
from pathlib import Path
from functools import reduce
import operator

from config import config
from config.feast import OfflineStoreType

def make_feature_view(
    name: str, 
    entities: list[Entity], 
    schema: list[Field],
    offline_store_path: str,
    online: bool = True, 
    ttl = timedelta(days=365)
) -> FeatureView:
    source = get_push_source(
        view_name=name, 
        offline_store_path=offline_store_path, 
        s3_endpoint=config.feast.feast_offline_store_s3_endpoint
    )

    fv = FeatureView(
        name=name,
        entities=entities,
        ttl=ttl,
        schema=schema,
        online=online, 
        source=source
    )

    if config.feast.feast_offline_store_type == OfflineStoreType.duckdb:
        init_file_source(fv, source.batch_source, s3_endpoint=config.feast.feast_offline_store_s3_endpoint)

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
        UnixTimestamp: pa.timestamp('s'),
    }

    if isinstance(_type, Array):
        return pa.list_(_feast_type_to_pa_type(_type.base_type))

    return type_mapping[_type]

def init_file_source(fv: FeatureView, source: FileSource, s3_endpoint: str | None = None):

    arrays = [pa.array([], pa.timestamp('s'))]
    schema = [('event_time', pa.timestamp('s'))]
    for entity in fv.entities:
        arrays.append(pa.array([], pa.int64()))
        schema.append((entity, pa.int64()))
    for field in fv.schema:
        arrays.append(pa.array([], _feast_type_to_pa_type(field.dtype)))
        schema.append((field.name, _feast_type_to_pa_type(field.dtype)))

    empty_table = pa.Table.from_arrays(arrays, schema=pa.schema(schema))

    if source.path.startswith('s3:'):
        import boto3
        parts = source.path[5:].split("/")
        bucket, key = (parts[0], "/".join(parts[1:]))

        writer = pa.BufferOutputStream()
        write_table(empty_table, writer)
        body = bytes(writer.getvalue())
        s3 = boto3.client("s3", endpoint_url=s3_endpoint)
        s3.put_object(Body=body, Bucket=bucket, Key=key)
    else:
        path = Path(source.path)
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)

        write_table(empty_table, source.path)

def get_push_source(view_name: str, offline_store_path: str, s3_endpoint: str | None = None) -> PushSource:
    batch_source = FileSource(
        name=f"{view_name}_source",
        path=f"{offline_store_path}/{view_name}.parquet",
        timestamp_field="event_time",
        file_format=ParquetFormat(),
        s3_endpoint_override=s3_endpoint
    )
    
    push_source = PushSource(
        name=f"{view_name}_stream",
        batch_source=batch_source,
    )

    return push_source

def push_to_offline_store(view_name, df):
    pass