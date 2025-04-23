
import os

from feast import FeatureView
from feast.types import (
    Int64, Float32, Float64, String, Bytes, Bool, Int32, UnixTimestamp, Array
)

import pyspark.sql.functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, ArrayType, FloatType, DoubleType
)
from pyspark.sql import SparkSession

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

def _feast_type_to_spark_type(dtype):
    if type(dtype) == Array:
        return ArrayType(_feast_type_to_spark_type(dtype.base_type))
    if dtype == Float32:
        return FloatType()
    return StringType()

def get_schema_from_fv(fv: FeatureView) -> StructType:
    schema = StructType()

    schema.add("event_time", LongType())
    for entity in fv.entities:
        schema.add(entity if type(entity) == str else entity.name, LongType())
    for field in fv.schema:
        schema.add(field.name.split('.')[-1], _feast_type_to_spark_type(field.dtype))
    
    return schema

def get_kafka_stream_reader(spark, bootstrap_servers: str, topic: str, starting_offset: str = 'earliest'):
    return (
        spark.readStream 
        .format("kafka") 
        .option("kafka.bootstrap.servers", bootstrap_servers)
        # .option("kafka.group.id", topic)
        .option("subscribe", topic) 
        .option("startingOffsets", starting_offset) 
        .load()
    )

def get_spark_streaming_session(app_name: str, s3_enabled: bool = False, s3_endpoint: str | None = None):
    spark = (
        SparkSession.builder
        .appName(app_name) 
        .config("spark.sql.adaptive.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("log4j.logger.org.apache.spark.sql.execution.streaming", "INFO")
    )

    packages = ["org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0"]

    if s3_enabled:
        packages += [
             "org.apache.hadoop:hadoop-aws:3.3.4",
             "com.amazonaws:aws-java-sdk-bundle:1.11.1026"
        ]
        spark = (
            spark
            .config("spark.hadoop.fs.s3a.access.key", os.environ['AWS_ACCESS_KEY_ID'])
            .config("spark.hadoop.fs.s3a.secret.key", os.environ['AWS_SECRET_ACCESS_KEY'])
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
        )

        if s3_endpoint:
            spark = spark.config("spark.hadoop.fs.s3a.endpoint", s3_endpoint)
    
    return (
        spark
        .config("spark.jars.packages", ",".join(packages))
        .getOrCreate()
    )