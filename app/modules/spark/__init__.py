
import pyspark.sql.functions as F
from pyspark.sql.types import StructType, StructField, StringType, LongType

def get_debezium_envelope_schema(item_schema: StructType):
    return StructType([
        StructField("schema", StructType(), nullable=True),
        StructField("payload", StructType([
            StructField("before", item_schema, nullable=True),
            StructField("after",  item_schema, nullable=True),
            StructField("op",     StringType(), nullable=True),
            StructField("ts_ms",  LongType(), nullable=True),
        ]), nullable=True)
    ])

def parse_debezium_payload(df, item_schema):
    return df.select(
        F.from_json(
            F.col("value").cast("string"), 
            get_debezium_envelope_schema(item_schema)
        ).alias("env")
    ).select(
        F.col("env.payload.before").alias('before'),
        F.col("env.payload.after").alias('after'),
        F.col("env.payload.op").alias('op'),
        F.col("env.payload.ts_ms").alias('ts_ms'),
    )