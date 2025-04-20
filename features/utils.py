
from feast import FeatureView, FileSource
from feast.types import (
    Int64, Float32, Float64, String, Bytes, Bool, Int32, UnixTimestamp
)
import pyarrow as pa
from pyarrow.parquet import ParquetDataset, write_table
from pathlib import Path
from functools import reduce
import operator

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
        UnixTimestamp: pa.timestamp('ns'),
    }
    return type_mapping[_type]

def init_file_source(fv: FeatureView, source: FileSource):
    path = Path(source.path)
    if path.exists():
        return
    arrays = [pa.array([], pa.timestamp('ns'))]
    schema = [('event_time', pa.timestamp('ns'))]
    for entity in fv.entities:
        arrays.append(pa.array([], pa.int64()))
        schema.append((entity, pa.int64()))
    for field in fv.schema:
        arrays.append(pa.array([], _feast_type_to_pa_type(field.dtype)))
        schema.append((field.name, _feast_type_to_pa_type(field.dtype)))

    empty_table = pa.Table.from_arrays(arrays, schema=pa.schema(schema))
    write_table(empty_table, str(path))
